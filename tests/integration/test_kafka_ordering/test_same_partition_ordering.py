"""Tests for same partition key message ordering in Kafka."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from confluent_kafka import Consumer, KafkaException, Producer
from testcontainers.kafka import KafkaContainer

SAME_KEY = "order-123"


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
@pytest.mark.integration
async def test_same_partition_key_preserves_ordering(
    docker_or_skip: None,
) -> None:
    """Test that messages with same partition key preserve ordering."""
    del docker_or_skip

    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")
    kafka.start(timeout=300)

    bootstrap = kafka.get_bootstrap_server()
    topic = f"test-ordering-{uuid4()}"
    group = f"ordering-test-{uuid4()}"

    producer = Producer(
        {
            "bootstrap.servers": bootstrap,
            "client.id": "ordering-test-producer",
        }
    )

    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([topic])

    try:
        # Produce 50 messages with same key
        for i in range(50):
            producer.produce(topic, value=f"msg-{i}".encode(), key=SAME_KEY.encode())
        producer.flush(timeout=30)

        # Consume and verify order
        received: list[str] = []
        start_time = asyncio.get_event_loop().time()

        while len(received) < 50 and (asyncio.get_event_loop().time() - start_time) < 60:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            if msg.error():
                raise KafkaException(msg.error())

            value = msg.value()
            if value is not None:
                received.append(value.decode())

        assert len(received) == 50, f"Expected 50 messages, got {len(received)}"

        # Extract sequence numbers and verify order
        values = [r.split("-")[1] for r in received]
        expected = [str(i) for i in range(50)]
        assert values == expected, f"Message order violated. Expected {expected}, got {values}"

    finally:
        consumer.close()
        kafka.stop()
