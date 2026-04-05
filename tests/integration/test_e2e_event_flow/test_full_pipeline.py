"""E2E test: full publish to outbox to Kafka to consume pipeline."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from testcontainers.kafka import KafkaContainer

from messaging.core.contracts import BaseEvent, EventRegistry
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from messaging.infrastructure.outbox.outbox_worker.worker import ScheduledOutboxWorker
from python_outbox_core import OutboxConfig


class E2ETestEvent(BaseEvent):
    event_type: str = "e2e.test_event"
    aggregate_id: str = "e2e-001"
    source: str = "e2e-test"
    test_value: str = "hello"


class RecordingPublisher:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def publish(self, message: dict[str, object]) -> None:
        self.messages.append(message)

    async def publish_to_topic(
        self,
        topic: str,
        message: dict[str, object],
    ) -> None:
        self.messages.append(message)


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_e2e_full_pipeline(
    docker_or_skip: None,
    sqlite_session_factory: tuple[
        object,
        async_sessionmaker[AsyncSession],
    ],
) -> None:
    del docker_or_skip
    _, factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(E2ETestEvent)
    repo = SqlAlchemyOutboxRepository(factory, registry)
    event = E2ETestEvent(test_value="e2e-data")
    await repo.add_event(event)
    unpublished = await repo.get_unpublished()
    assert len(unpublished) == 1
    kafka = KafkaContainer()
    kafka.start(timeout=300)
    bootstrap = kafka.get_bootstrap_server()
    topic = f"e2e-{uuid4()}"
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=f"e2e-{uuid4()}",
        auto_offset_reset="earliest",
    )
    publisher = RecordingPublisher()
    worker = ScheduledOutboxWorker(
        repo,
        publisher,
        OutboxConfig(
            batch_size=10,
            poll_interval_seconds=1,
            max_retry_count=0,
            retry_backoff_multiplier=1.0,
        ),
    )
    await worker.publish_batch()
    assert len(publisher.messages) == 1
    produced = json.dumps(publisher.messages[0]).encode()
    kafka_producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    await kafka_producer.start()
    try:
        await kafka_producer.send_and_wait(topic, value=produced)
        await consumer.start()
        rec = await asyncio.wait_for(consumer.getone(), timeout=30)
        received = json.loads(rec.value.decode())
        assert received["eventType"] == event.event_type
        assert received["aggregateId"] == event.aggregate_id
    finally:
        await consumer.stop()
        await kafka_producer.stop()
        kafka.stop()
