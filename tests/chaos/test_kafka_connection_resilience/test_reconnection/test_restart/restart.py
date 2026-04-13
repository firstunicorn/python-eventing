"""Kafka restart and recovery helpers."""

import asyncio

from testcontainers.kafka import KafkaContainer

from .setup import create_topic_and_verify


async def restart_kafka_and_recreate_topic(kafka: KafkaContainer, topic: str) -> str:
    """Restart Kafka container and recreate topic.

    Args:
        kafka: Kafka container instance
        topic: Topic to recreate

    Returns:
        New bootstrap servers address
    """
    kafka.stop()
    await asyncio.sleep(5)

    kafka.start(timeout=300)
    await asyncio.sleep(60)

    bootstrap_servers = kafka.get_bootstrap_server()

    await create_topic_and_verify(bootstrap_servers, topic)

    await asyncio.sleep(5)

    return bootstrap_servers
