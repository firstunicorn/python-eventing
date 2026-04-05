"""Integration test for consumer group offset commit and resume behavior."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from testcontainers.kafka import KafkaContainer


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
async def test_offset_commit_and_resume(
    docker_or_skip: None,
) -> None:
    del docker_or_skip
    kafka = KafkaContainer()
    kafka.start(timeout=1800)
    bootstrap = kafka.get_bootstrap_server()
    topic = f"offset-test-{uuid4()}"
    group = f"offset-group-{uuid4()}"
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    await producer.start()
    for i in range(5):
        await producer.send_and_wait(
            topic,
            value=json.dumps({"idx": i}).encode(),
            key=b"key-1",
        )
    await asyncio.sleep(3)
    consumer1 = AIOKafkaConsumer(
        topic, bootstrap_servers=bootstrap, group_id=group,
        auto_offset_reset="earliest", enable_auto_commit=True,
    )
    await consumer1.start()
    try:
        received: list[int] = []
        for _ in range(5):
            record = await asyncio.wait_for(consumer1.getone(), timeout=30)
            received.append(json.loads(record.value.decode())["idx"])
        assert sorted(received) == list(range(5))
    finally:
        await consumer1.stop()
    await asyncio.sleep(5)
    consumer2 = AIOKafkaConsumer(
        topic, bootstrap_servers=bootstrap, group_id=group,
        auto_offset_reset="latest", enable_auto_commit=True,
    )
    await consumer2.start()
    try:
        for i in range(5, 10):
            await producer.send_and_wait(
                topic,
                value=json.dumps({"idx": i}).encode(),
                key=b"key-1",
            )
        await asyncio.sleep(5)
        new_events: list[int] = []
        for _ in range(5):
            record = await asyncio.wait_for(consumer2.getone(), timeout=30)
            new_events.append(json.loads(record.value.decode())["idx"])
        assert all(idx >= 5 for idx in new_events)
        assert sorted(new_events) == list(range(5, 10))
    finally:
        await consumer2.stop()
        await producer.stop()
        kafka.stop()
