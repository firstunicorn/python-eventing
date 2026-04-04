"""Kafka-backed event publisher built on FastStream.

This module provides the `KafkaEventPublisher` which handles routing
events to their corresponding Kafka topics based on their event types,
along with serialization and partition key extraction.

See also
--------
- messaging.infrastructure.pubsub.broker_config : Kafka broker setup
- messaging.infrastructure.outbox.outbox_worker : Background publisher
"""

from __future__ import annotations

import logging
from typing import Any

from faststream.kafka import KafkaBroker

from python_outbox_core import IEventPublisher

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class KafkaEventPublisher(IEventPublisher):
    """Publish serialized events to Kafka topics derived from event type."""

    def __init__(self, broker: KafkaBroker) -> None:
        self._broker = broker

    async def publish(self, message: dict[str, Any]) -> None:
        """Publish a message to its default event topic."""
        topic = self._resolve_topic(message)
        logger.debug("Publishing message to topic '%s'", topic)
        await self.publish_to_topic(topic, message)

    async def publish_to_topic(self, topic: str, message: dict[str, Any]) -> None:
        """Publish a message to an explicit Kafka topic."""
        key = message.get("aggregateId") or message.get("aggregate_id")
        # FastStream Kafka requires bytes for partition keys
        key_bytes = key.encode("utf-8") if isinstance(key, str) else key
        logger.debug("Publishing to topic='%s', key=%s", topic, key)
        await self._broker.publish(
            message,
            topic=topic,
            key=key_bytes,
        )

    @staticmethod
    def _resolve_topic(message: dict[str, Any]) -> str:
        return str(message.get("eventType") or message.get("event_type") or "domain-events")
