"""Test different-group consumers each receive all messages."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from testcontainers.kafka import KafkaContainer


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
async def test_different_groups_both_receive_all(
    docker_or_skip: None,
) -> None:
    del docker_or_skip
    kafka = KafkaContainer()
    kafka.start(timeout=1800)
    bootstrap = kafka.get_bootstrap_server()
    topic = f"test-diff-grp-{uuid4()}"
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    c1 = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=f"grp-a-{uuid4()}",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    c2 = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=f"grp-b-{uuid4()}",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await producer.start()
    await c1.start()
    await c2.start()
    try:
        for i in range(10):
            await producer.send_and_wait(topic, value=f"m-{i}".encode())
        await asyncio.sleep(5)
        r1 = {
            m.value.decode()
            for m in [await asyncio.wait_for(c1.getone(), timeout=10) for _ in range(10)]
        }
        r2 = {
            m.value.decode()
            for m in [await asyncio.wait_for(c2.getone(), timeout=10) for _ in range(10)]
        }
        assert r1 == {f"m-{i}" for i in range(10)}
        assert r2 == r1
    finally:
        await c1.stop()
        await c2.stop()
        await producer.stop()
        kafka.stop()
