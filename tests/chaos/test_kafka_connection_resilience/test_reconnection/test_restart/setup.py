"""Setup helpers for Kafka restart resilience test."""

import asyncio
from uuid import uuid4

from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic


async def create_topic_and_verify(bootstrap_servers: str, topic: str) -> None:
    """Create a Kafka topic and wait for it to be ready.

    Args:
        bootstrap_servers: Kafka bootstrap servers
        topic: Topic name to create

    Raises:
        Exception: If topic creation or verification fails
    """
    admin = AdminClient({"bootstrap.servers": bootstrap_servers})
    new_topic = NewTopic(topic, num_partitions=1, replication_factor=1)
    fs = admin.create_topics([new_topic], request_timeout=30.0)

    for _topic_name, future in fs.items():
        try:
            future.result()
        except Exception as e:
            if "TOPIC_ALREADY_EXISTS" not in str(e):
                raise

    await asyncio.sleep(3)


async def produce_and_consume_init_message(bootstrap_servers: str, topic: str) -> None:
    """Produce and consume an initial message to verify topic is ready.

    Args:
        bootstrap_servers: Kafka bootstrap servers
        topic: Topic to use
    """
    producer_init = Producer({"bootstrap.servers": bootstrap_servers})
    producer_init.produce(topic, value=b"init")
    producer_init.flush(timeout=10)

    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": f"c-pub-recon-{uuid4()}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([topic])

    await asyncio.sleep(2)
    msg = consumer.poll(timeout=5.0)
    if msg and not msg.error():
        consumer.commit(msg)
    consumer.close()
