"""Docker-gated Testcontainers smoke tests for eventing."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from confluent_kafka import Consumer
from testcontainers.kafka import KafkaContainer

from tests.integration.test_testcontainers_smoke.fixtures import (
    TEST_MESSAGE,
    TEST_TOPIC,
    ExampleEvent,
)

from .setup import create_postgres_container, setup_containers_and_infrastructure
from .verification import verify_message_received


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
@pytest.mark.integration
async def test_postgres_and_kafka_testcontainers_support_eventing_smoke(
    docker_or_skip: None,
) -> None:
    """A live broker and database should support storage plus real FastStream publishing."""
    del docker_or_skip

    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")

    with create_postgres_container() as postgres:
        (
            engine,
            session_factory,
            broker,
            repository,
            publisher,
            bootstrap_servers,
        ) = await setup_containers_and_infrastructure(kafka, postgres)

        try:
            await publisher.publish(TEST_MESSAGE)

            await asyncio.sleep(2)

            consumer = Consumer(
                {
                    "bootstrap.servers": bootstrap_servers,
                    "group.id": f"eventing-test-{uuid4()}",
                    "auto.offset.reset": "earliest",
                    "enable.auto.commit": False,
                }
            )
            consumer.subscribe([TEST_TOPIC])

            await repository.add_event(ExampleEvent(xp_delta=15))

            assert await broker.ping(1.0) is True

            await verify_message_received(consumer, TEST_TOPIC, b"user-123")

        finally:
            try:
                consumer.close()
            except NameError:
                pass
            await broker.stop()
            await engine.dispose()
            kafka.stop()
