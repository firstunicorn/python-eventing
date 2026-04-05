"""Test same-group consumers distribute messages without duplicates."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from testcontainers.kafka import KafkaContainer


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
async def test_same_group_distributes_messages(
    docker_or_skip: None,
) -> None:
    del docker_or_skip
    kafka = KafkaContainer()
    kafka.start(timeout=1800)
    bootstrap = kafka.get_bootstrap_server()
    topic = f"test-group-{uuid4()}"
    group = f"group-shared-{uuid4()}"
    consumer1 = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=group,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    consumer2 = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=group,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer1.start()
    await consumer2.start()
    await asyncio.sleep(5)
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    await producer.start()
    try:
        seen1: set[str] = set()
        seen2: set[str] = set()
        for i in range(20):
            await producer.send_and_wait(
                topic, value=f"evt-{i}".encode(), key=f"key-{i % 2}".encode()
            )
        await asyncio.sleep(10)
        async for record in consumer1:
            seen1.add(record.value.decode())
            if len(seen1) + len(seen2) >= 20:
                break
            if len(seen1) > 18:
                break
        async for record in consumer2:
            seen2.add(record.value.decode())
            if len(seen1) + len(seen2) >= 20:
                break
            if len(seen2) > 18:
                break
        total = len(seen1) + len(seen2)
        assert total >= 19
        assert not (seen1 & seen2), "same-group consumers got duplicates"
    finally:
        await consumer1.stop()
        await consumer2.stop()
        await producer.stop()
        kafka.stop()
