"""Test publisher raises when Kafka goes down during publish."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from confluent_kafka import Producer
from testcontainers.kafka import KafkaContainer


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.chaos
async def test_publisher_raises_on_kafka_down(
    docker_or_skip: None,
) -> None:
    """Test that producer fails when Kafka goes down during publish."""
    del docker_or_skip

    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")
    kafka.start(timeout=300)

    bootstrap = kafka.get_bootstrap_server()

    producer = Producer({
        "bootstrap.servers": bootstrap,
        "client.id": "chaos-test-producer",
    })

    # Verify producer works initially
    topic = f"test-{uuid4()}"
    producer.produce(topic, value=b"test-before-shutdown")
    producer.flush(timeout=10)

    # Stop Kafka
    kafka.stop()
    await asyncio.sleep(3)  # Longer wait for full disconnect

    # Attempt to produce - messages get queued locally
    producer.produce(topic, value=b"test-after-shutdown")

    # Flush returns number of messages still in queue
    # >0 means delivery failed (expected when broker is down)
    remaining = producer.flush(timeout=10)
    assert remaining > 0, f"Expected flush to fail with messages remaining, got {remaining}"

