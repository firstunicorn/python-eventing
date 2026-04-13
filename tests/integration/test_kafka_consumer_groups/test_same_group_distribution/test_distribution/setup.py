"""Setup helpers for consumer group distribution test."""

import asyncio
from uuid import uuid4

from confluent_kafka import Consumer, Producer
from testcontainers.kafka import KafkaContainer


async def setup_kafka_with_topic(kafka: KafkaContainer):
    """Set up Kafka container and create test topic.

    Returns:
        Tuple of (bootstrap_servers, topic, group_id)
    """
    bootstrap = kafka.get_bootstrap_server()
    topic = f"test-group-{uuid4()}"
    group = f"group-shared-{uuid4()}"

    producer_setup = Producer(
        {
            "bootstrap.servers": bootstrap,
            "client.id": "setup-producer",
        }
    )
    producer_setup.produce(topic, value=b"setup")
    producer_setup.flush(timeout=10)

    await asyncio.sleep(5)

    return bootstrap, topic, group


def create_consumer(bootstrap_servers: str, group_id: str, topic: str) -> Consumer:
    """Create and subscribe a Kafka consumer to a topic.

    Args:
        bootstrap_servers: Kafka bootstrap servers
        group_id: Consumer group ID
        topic: Topic to subscribe to

    Returns:
        Configured and subscribed Consumer instance
    """
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe([topic])
    return consumer
