"""Kafka-backed event publisher built on FastStream.

This module provides the `KafkaEventPublisher` which handles routing
events to their corresponding Kafka topics based on their event types,
along with serialization and partition key extraction.

See also
--------
- eventing.infrastructure.messaging.broker_config : Kafka broker setup
- eventing.infrastructure.outbox.outbox_worker : Background publisher
"""

from __future__ import annotations

from typing import Any

from faststream.kafka import KafkaBroker

from python_outbox_core import IEventPublisher


class KafkaEventPublisher(IEventPublisher):
    """Publish serialized events to Kafka topics derived from event type."""

    def __init__(self, broker: KafkaBroker) -> None:
        self._broker = broker

    async def publish(self, message: dict[str, Any]) -> None:
        """Publish a message to its default event topic."""
        await self.publish_to_topic(self._resolve_topic(message), message)

    async def publish_to_topic(self, topic: str, message: dict[str, Any]) -> None:
        """Publish a message to an explicit Kafka topic."""
        await self._broker.publish(
            message,
            topic=topic,
            key=message.get("aggregateId") or message.get("aggregate_id"),
        )

    @staticmethod
    def _resolve_topic(message: dict[str, Any]) -> str:
        return str(message.get("eventType") or message.get("event_type") or "domain-events")
