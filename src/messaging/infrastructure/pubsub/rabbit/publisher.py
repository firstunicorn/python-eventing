"""RabbitMQ event publisher using FastStream RabbitBroker."""

from typing import Any

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange

from messaging.core.contracts.base_event import BaseEvent


class RabbitEventPublisher:
    """Publishes events to RabbitMQ exchanges with routing keys."""

    def __init__(
        self,
        broker: RabbitBroker,
        default_exchange: str | RabbitExchange = "events",
    ) -> None:
        """Initialize RabbitMQ publisher.

        Args:
            broker: FastStream RabbitBroker instance.
            default_exchange: Default exchange for publishing events.
        """
        self._broker = broker

        # BUG FIX: Explicit TOPIC exchange type when string is passed.
        # Bare string "events" caused FastStream to use implicit DIRECT exchange.
        # DIRECT requires exact routing key match; test queue bound to TOPIC pattern.
        # Publish succeeded silently but message routed to wrong exchange type.
        if isinstance(default_exchange, str):
            self._default_exchange = RabbitExchange(
                default_exchange, type=ExchangeType.TOPIC, durable=True
            )
        else:
            self._default_exchange = default_exchange

    async def publish_to_exchange(
        self,
        event: BaseEvent | dict[str, Any],
        routing_key: str,
        exchange: str | RabbitExchange | None = None,
    ) -> None:
        """Publish event to RabbitMQ exchange with routing key.

        Args:
            event: Event to publish (BaseEvent or dict).
            routing_key: Routing key for message routing.
            exchange: Optional exchange override (defaults to default_exchange).
        """
        target_exchange = exchange or self._default_exchange

        # Convert BaseEvent to dict if needed
        payload = event.model_dump() if isinstance(event, BaseEvent) else event

        await self._broker.publish(
            message=payload,
            exchange=target_exchange,
            routing_key=routing_key,
        )

    async def publish(
        self,
        event: BaseEvent | dict[str, Any],
        routing_key: str | None = None,
    ) -> None:
        """Publish event to default exchange.

        Args:
            event: Event to publish.
            routing_key: Optional routing key (defaults to event type).
        """
        # Use event type as routing key if not specified
        if routing_key is None:
            if isinstance(event, BaseEvent):
                routing_key = event.event_type
            else:
                routing_key = event.get("event_type", "unknown")

        await self.publish_to_exchange(event, routing_key)
