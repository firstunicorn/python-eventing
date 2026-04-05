"""Test publisher works after Kafka container restart."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from testcontainers.kafka import KafkaContainer


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.chaos
async def test_publisher_works_after_kafka_restart(
    docker_or_skip: None,
) -> None:
    del docker_or_skip
    kafka = KafkaContainer()
    kafka.start(timeout=1800)
    bootstrap1 = kafka.get_bootstrap_server()
    topic = f"pub-recon-{uuid4()}"
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap1,
        group_id=f"c-pub-recon-{uuid4()}",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    kafka.stop()
    await asyncio.sleep(5)
    kafka.start()
    await asyncio.sleep(10)
    await consumer.stop()
    bootstrap2 = kafka.get_bootstrap_server()
    consumer2 = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap2,
        group_id=f"c-pub-recon2-{uuid4()}",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer2.start()
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap2)
    await producer.start()
    await producer.send_and_wait(topic, value=b"recovered")
    try:
        record = await asyncio.wait_for(consumer2.getone(), timeout=30)
        assert record.value == b"recovered"
    finally:
        await consumer2.stop()
        await producer.stop()
        kafka.stop()
