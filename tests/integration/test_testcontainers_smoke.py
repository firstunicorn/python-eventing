"""Docker-gated Testcontainers smoke tests for eventing."""

from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer  # type: ignore[import-untyped]
from testcontainers.kafka import KafkaContainer  # type: ignore[import-untyped]
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from messaging.config import Settings
from messaging.core.contracts import BaseEvent, EventRegistry
from messaging.infrastructure.pubsub import KafkaEventPublisher, create_kafka_broker
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from messaging.infrastructure.persistence.orm_models.orm_base import Base
from messaging.infrastructure.persistence.session import create_session_factory


TEST_TOPIC = "gamification.XPAwarded"
TEST_MESSAGE = {
    "eventType": TEST_TOPIC,
    "aggregateId": "user-123",
    "source": "gamification-service",
    "xpDelta": 15,
}


class ExampleEvent(BaseEvent):  # pylint: disable=too-many-ancestors
    """Concrete event used for container-backed smoke coverage."""

    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "user-123"
    source: str = "gamification-service"
    xp_delta: int


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
async def test_postgres_and_kafka_testcontainers_support_eventing_smoke(
    docker_or_skip: None,
) -> None:
    """A live broker and database should support storage plus real FastStream publishing."""
    del docker_or_skip
    kafka = KafkaContainer()
    with PostgresContainer(
        "postgres:16",
        username="postgres",
        password=os.getenv("TESTCONTAINERS_POSTGRES_PASSWORD", "postgres"),
        dbname="eventing",
    ) as postgres:
        kafka.start(timeout=1800)
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
        registry = EventRegistry()
        registry.register(ExampleEvent)
        repository = SqlAlchemyOutboxRepository(session_factory, registry)
        publisher = KafkaEventPublisher(broker)
        consumer = AIOKafkaConsumer(
            TEST_TOPIC,
            bootstrap_servers=bootstrap_servers,
            group_id=f"eventing-test-{uuid4()}",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        try:
            await consumer.start()
            await broker.connect()
            await broker.start()
            await repository.add_event(ExampleEvent(xp_delta=15))
            pending = await repository.get_unpublished()
            assert len(pending) == 1
            assert await broker.ping(1.0) is True
            await publisher.publish(TEST_MESSAGE)
            record = await asyncio.wait_for(consumer.getone(), timeout=30)
            assert record.topic == TEST_TOPIC
            assert record.key == b"user-123"
            assert json.loads(record.value.decode("utf-8"))["eventType"] == TEST_TOPIC
        finally:
            await consumer.stop()
            await broker.stop()
            await engine.dispose()
            kafka.stop()
