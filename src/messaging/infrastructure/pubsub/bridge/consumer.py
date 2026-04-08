"""Kafka-to-RabbitMQ bridge consumer."""

from typing import Any

from messaging.infrastructure.pubsub import IProcessedMessageStore
from messaging.infrastructure.pubsub.bridge.routing_key_builder import (
    build_routing_key,
)


class BridgeConsumer:
    """Consume events from Kafka and route to RabbitMQ with idempotency."""

    def __init__(
        self,
        rabbit_publisher: Any,  # RabbitMQ publisher (not yet implemented)
        processed_message_store: IProcessedMessageStore,
        routing_key_template: str = "{event_type}",
    ) -> None:
        """Initialize bridge consumer.

        Args:
            rabbit_publisher: RabbitMQ event publisher
            processed_message_store: Store for idempotency tracking
            routing_key_template: Template for building RabbitMQ routing keys
        """
        self._rabbit_publisher = rabbit_publisher
        self._processed_store = processed_message_store
        self._routing_template = routing_key_template

    async def handle_message(self, message: dict[str, Any]) -> None:
        """Handle message from Kafka by routing to RabbitMQ.

        Args:
            message: Event message from Kafka
        """
        event_id = message.get("event_id") or message.get("eventId")
        if not event_id:
            # Skip malformed messages without event ID
            return

        # Check idempotency
        is_new = await self._processed_store.claim(
            consumer_name="kafka_rabbitmq_bridge", event_id=event_id
        )
        if not is_new:
            return  # Already processed

        # Build routing key and publish to RabbitMQ
        routing_key = build_routing_key(self._routing_template, message)
        await self._rabbit_publisher.publish_to_exchange(message, routing_key)
