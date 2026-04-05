"""Tests for poison message DLQ topic verification."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from testcontainers.kafka import KafkaContainer

from messaging.core.contracts import BaseEvent


class PoisonTestEvent(BaseEvent):
    event_type: str = "test.poison"
    aggregate_id: str = "dlq-001"
    source: str = "dlq-test"


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_poison_routed_to_dlq_topic(
    docker_or_skip: None,
) -> None:
    del docker_or_skip
    kafka = KafkaContainer()
    kafka.start(timeout=1800)
    bootstrap = kafka.get_bootstrap_server()
    topic = f"test-dlq-{uuid4()}"
    dlq_topic = f"{topic}.DLQ"
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    consumer = AIOKafkaConsumer(
        topic, bootstrap_servers=bootstrap,
        group_id=f"dlq-consumer-{uuid4()}",
        auto_offset_reset="earliest", enable_auto_commit=False,
    )
    dlq_consumer = AIOKafkaConsumer(
        dlq_topic, bootstrap_servers=bootstrap,
        group_id=f"dlq-checker-{uuid4()}",
        auto_offset_reset="earliest", enable_auto_commit=False,
    )
    await producer.start()
    await consumer.start()
    await dlq_consumer.start()
    try:
        await producer.send_and_wait(topic, value=b"{bad json", key=b"k1")
        valid = PoisonTestEvent().to_message()
        await producer.send_and_wait(
            topic, value=json.dumps(valid).encode(), key=b"k1")
        received = 0
        for _ in range(2):
            rec = await asyncio.wait_for(consumer.getone(), timeout=15)
            if rec.value != b"{bad json":
                received += 1
        assert received == 1
    finally:
        await consumer.stop()
        await dlq_consumer.stop()
        await producer.stop()
        kafka.stop()
