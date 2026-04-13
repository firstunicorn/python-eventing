"""Test publisher works after Kafka container restart."""

from __future__ import annotations

from uuid import uuid4

import pytest
from confluent_kafka import Consumer, Producer
from testcontainers.kafka import KafkaContainer

from .restart import restart_kafka_and_recreate_topic
from .setup import create_topic_and_verify, produce_and_consume_init_message
from .verification import produce_and_verify_message_after_restart


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.chaos
async def test_publisher_works_after_kafka_restart(
    docker_or_skip: None,
) -> None:
    """Test that producer/consumer work after Kafka restart (chaos resilience)."""
    del docker_or_skip

    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")
    kafka.start(timeout=300)

    bootstrap1 = kafka.get_bootstrap_server()
    topic = f"pub-recon-{uuid4()}"

    await create_topic_and_verify(bootstrap1, topic)

    await produce_and_consume_init_message(bootstrap1, topic)

    bootstrap2 = await restart_kafka_and_recreate_topic(kafka, topic)

    consumer2 = Consumer(
        {
            "bootstrap.servers": bootstrap2,
            "group.id": f"c-pub-recon2-{uuid4()}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "session.timeout.ms": "45000",
            "metadata.max.age.ms": "5000",
        }
    )
    consumer2.subscribe([topic])

    producer = Producer(
        {
            "bootstrap.servers": bootstrap2,
            "client.id": "chaos-test-producer",
            "socket.timeout.ms": "60000",
        }
    )

    try:
        await produce_and_verify_message_after_restart(producer, consumer2, topic)

    finally:
        consumer2.close()
        kafka.stop()
