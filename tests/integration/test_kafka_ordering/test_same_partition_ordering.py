"""Tests for same partition key message ordering in Kafka."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from testcontainers.kafka import KafkaContainer

SAME_KEY = "order-123"


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
async def test_same_partition_key_preserves_ordering(
    docker_or_skip: None,
) -> None:
    del docker_or_skip
    kafka = KafkaContainer()
    kafka.start(timeout=1800)
    bootstrap = kafka.get_bootstrap_server()
    topic = f"test-ordering-{uuid4()}"
    group = f"ordering-test-{uuid4()}"
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=group,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await producer.start()
    await consumer.start()
    try:
        for i in range(50):
            await producer.send_and_wait(topic, value=f"msg-{i}".encode(), key=SAME_KEY.encode())
        received: list[str] = []
        for _ in range(50):
            record = await asyncio.wait_for(consumer.getone(), timeout=10)
            received.append(record.value.decode())
        values = [r.split("-")[1] for r in received]
        assert values == [str(i) for i in range(50)]
    finally:
        await consumer.stop()
        await producer.stop()
        kafka.stop()
