"""Docker-gated Testcontainers smoke tests for eventing."""

from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

import pytest
from confluent_kafka import Consumer, KafkaException
from testcontainers.kafka import KafkaContainer
from testcontainers.postgres import PostgresContainer

from messaging.config import Settings
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from messaging.infrastructure.persistence.orm_models.orm_base import Base
from messaging.infrastructure.persistence.session import create_session_factory
from messaging.infrastructure.pubsub import KafkaEventPublisher, create_kafka_broker
from tests.integration.test_testcontainers_smoke.fixtures import (
    TEST_MESSAGE,
    TEST_TOPIC,
    ExampleEvent,
)


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
@pytest.mark.integration
async def test_postgres_and_kafka_testcontainers_support_eventing_smoke(
    docker_or_skip: None,
) -> None:
    """A live broker and database should support storage plus real FastStream publishing."""
    del docker_or_skip
    
    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")
    
    with PostgresContainer(
        "postgres:16",
        username="postgres",
        password=os.getenv("TESTCONTAINERS_POSTGRES_PASSWORD", "postgres"),
        dbname="eventing",
    ) as postgres:
        kafka.start(timeout=300)
        
        engine, session_factory = create_session_factory(
            postgres.get_connection_url(driver="asyncpg")
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        
        bootstrap_servers = kafka.get_bootstrap_server()
        
        broker = create_kafka_broker(
            Settings(
                kafka_bootstrap_servers=bootstrap_servers,
                kafka_client_id="eventing-test",
            )
        )
        
        repository = SqlAlchemyOutboxRepository(session_factory)
        publisher = KafkaEventPublisher(broker)
        
        consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': f"eventing-test-{uuid4()}",
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
        })
        consumer.subscribe([TEST_TOPIC])
        
        try:
            await broker.connect()
            await broker.start()
            
            await repository.add_event(ExampleEvent(xp_delta=15))
            
            assert await broker.ping(1.0) is True
            
            await publisher.publish(TEST_MESSAGE)
            
            # Poll for message with timeout
            start_time = asyncio.get_event_loop().time()
            message_received = False
            
            while (asyncio.get_event_loop().time() - start_time) < 30:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    await asyncio.sleep(0.1)
                    continue
                if msg.error():
                    raise KafkaException(msg.error())
                
                assert msg.topic() == TEST_TOPIC
                assert msg.key() == b"user-123"
                
                value = msg.value()
                assert value is not None
                payload = json.loads(value.decode("utf-8"))
                assert payload["eventType"] == TEST_TOPIC
                
                message_received = True
                break
            
            assert message_received, "Message not received within timeout"
            
        finally:
            consumer.close()
            await broker.stop()
            await engine.dispose()
            kafka.stop()
