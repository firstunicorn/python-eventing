"""Verification helpers for testcontainers smoke test."""

import asyncio
import json

from confluent_kafka import Consumer, KafkaException


async def verify_message_received(consumer: Consumer, expected_topic: str, expected_key: bytes) -> None:
    """Poll for Kafka message and verify its contents.

    Args:
        consumer: Kafka consumer instance
        expected_topic: Expected message topic
        expected_key: Expected message key

    Raises:
        AssertionError: If message not received or contents don't match
    """
    start_time = asyncio.get_event_loop().time()
    message_received = False

    while (asyncio.get_event_loop().time() - start_time) < 30:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            await asyncio.sleep(0.1)
            continue
        if msg.error():
            raise KafkaException(msg.error())

        assert msg.topic() == expected_topic
        assert msg.key() == expected_key

        value = msg.value()
        assert value is not None
        payload = json.loads(value.decode("utf-8"))
        assert payload["eventType"] == expected_topic

        message_received = True
        break

    assert message_received, "Message not received within timeout"
