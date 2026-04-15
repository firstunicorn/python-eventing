"""Kafka-backed event publisher built on FastStream.

This module provides the `KafkaEventPublisher` which handles routing
events to their corresponding Kafka topics based on their event types,
along with serialization and partition key extraction.

See Also
--------
- messaging.infrastructure.pubsub.broker_config : Kafka broker setup
- messaging.infrastructure.outbox.outbox_worker : Background publisher
"""

from __future__ import annotations

import logging
from typing import Any

from faststream.confluent import KafkaBroker

from python_outbox_core import IEventPublisher

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class KafkaEventPublisher(IEventPublisher):
    """Publish serialized events to Kafka topics derived from event type.
    
    IMPORTANT: FastStream's broker.publish() does not flush by default for performance.
    For guaranteed delivery (e.g., manual replay operations), either:
    
    1. Use autoflush=True when creating publishers:
       publisher = broker.publisher("topic", autoflush=True)
       
    2. Or use confluent_kafka.Producer with explicit flush():
       producer = Producer({...})
       producer.produce(topic, value)
       producer.flush(timeout=10.0)
    
    Normal event publishing uses Kafka Connect CDC (not this class), so autoflush
    is not critical for main application flow.
    
    See: 
    - FastStream autoflush: https://faststream.ag2.ai/latest/api/faststream/confluent/broker/broker/KafkaBroker/
    - E2E test pattern: scripts/tests/e2e_v2/producer_service_v2.py
    """

    def __init__(self, broker: KafkaBroker, autoflush: bool = False) -> None:
        """Initialize publisher with optional autoflush.
        
        Args:
            broker: FastStream Kafka broker instance
            autoflush: If True, flush after every publish (default: False)
        """
        self._broker = broker
        self._autoflush = autoflush

    async def publish(self, message: dict[str, Any]) -> None:
        """Publish a message to its default event topic."""
        topic = self._resolve_topic(message)
        logger.debug("Publishing message to topic '%s'", topic)
        await self.publish_to_topic(topic, message)

    async def publish_to_topic(self, topic: str, message: dict[str, Any]) -> None:
        """Publish a message to an explicit Kafka topic.
        
        If autoflush=True, the underlying Kafka producer will flush after this call.
        Otherwise, messages are buffered for batching (better performance but no
        immediate delivery guarantee).
        """
        key = message.get("aggregateId") or message.get("aggregate_id")
        # FastStream Kafka requires bytes for partition keys
        key_bytes = key.encode("utf-8") if isinstance(key, str) else key
        logger.debug("Publishing to topic='%s', key=%s, autoflush=%s", topic, key, self._autoflush)
        
        # Create publisher with autoflush if enabled
        if self._autoflush:
            publisher = self._broker.publisher(topic, autoflush=True)
            await publisher.publish(message, key=key_bytes)
        else:
            # Use broker.publish() directly (no flush, buffered)
            await self._broker.publish(
                message,
                topic=topic,
                key=key_bytes,
            )

    @staticmethod
    def _resolve_topic(message: dict[str, Any]) -> str:
        return str(message.get("eventType") or message.get("event_type") or "domain-events")
