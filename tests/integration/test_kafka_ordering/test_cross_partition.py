"""Tests for cross-partition key ordering in Kafka (no cross-partition guarantee)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from testcontainers.kafka import KafkaContainer

SAME_KEY = "order-123"
OTHER_KEY = "order-456"


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
async def test_different_partition_keys_no_cross_order(
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
        for i in range(20):
            await producer.send_and_wait(topic, value=f"a-{i}".encode(), key=SAME_KEY.encode())
            await producer.send_and_wait(topic, value=f"b-{i}".encode(), key=OTHER_KEY.encode())
        a_keys: list[int] = []
        b_keys: list[int] = []
        for _ in range(40):
            record = await asyncio.wait_for(consumer.getone(), timeout=10)
            val = record.value.decode()
            k = record.key.decode()
            if k == SAME_KEY:
                a_keys.append(int(val.split("-")[1]))
            else:
                b_keys.append(int(val.split("-")[1]))
        assert a_keys == list(range(20))
        assert b_keys == list(range(20))
    finally:
        await consumer.stop()
        await producer.stop()
        kafka.stop()
