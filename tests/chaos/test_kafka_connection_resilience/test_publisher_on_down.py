"""Test publisher raises when Kafka goes down during publish."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaProducer
from testcontainers.kafka import KafkaContainer


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.chaos
async def test_publisher_raises_on_kafka_down(
    docker_or_skip: None,
) -> None:
    del docker_or_skip
    kafka = KafkaContainer()
    kafka.start(timeout=1800)
    bootstrap = kafka.get_bootstrap_server()
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    await producer.start()
    kafka.stop()
    await asyncio.sleep(2)
    with pytest.raises(Exception):  # noqa: B017,PT011 - any error acceptable for chaos test
        await asyncio.wait_for(producer.send_and_wait(f"test-{uuid4()}", value=b"test"), timeout=10)
    await producer.stop()
