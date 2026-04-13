"""Test same-group consumers distribute messages without duplicates."""

from __future__ import annotations

import asyncio

import pytest
from confluent_kafka import Producer
from testcontainers.kafka import KafkaContainer

from .messages import consume_and_collect_messages, produce_test_messages, verify_distribution
from .setup import create_consumer, setup_kafka_with_topic


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
@pytest.mark.integration
async def test_same_group_distributes_messages(
    docker_or_skip: None,
) -> None:
    """Test that same consumer group distributes messages without duplicates."""
    del docker_or_skip

    await asyncio.sleep(10)

    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")

    try:
        kafka.start(timeout=300)
    except RuntimeError as e:
        if "exited" in str(e):
            pytest.skip(f"Docker resource exhaustion: {e}")
        raise

    bootstrap, topic, group = await setup_kafka_with_topic(kafka)

    consumer1 = create_consumer(bootstrap, group, topic)
    consumer2 = create_consumer(bootstrap, group, topic)

    await asyncio.sleep(5)

    producer = Producer(
        {
            "bootstrap.servers": bootstrap,
            "client.id": "test-producer",
        }
    )

    try:
        await produce_test_messages(producer, topic, 20)

        seen1, seen2 = await consume_and_collect_messages(consumer1, consumer2, max_polls=60)

        verify_distribution(seen1, seen2, expected_min=19)

    finally:
        consumer1.close()
        consumer2.close()
        try:
            kafka.stop()
        except Exception:
            pass
