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

        # BUG FIX: Explicitly declare exchange type as TOPIC when string is passed
        # ISSUE: test_kafka_rabbitmq_bridge was failing with QueueEmpty even after
        #        fixing race condition (queue setup before publish).
        # ROOT CAUSE: When default_exchange is a bare string "events", FastStream's
        #             broker.publish() uses an IMPLICIT exchange type (defaults to DIRECT).
        #             DIRECT exchanges require exact routing key match, but our test queue
        #             was bound with routing_key="user.created" to a TOPIC exchange pattern.
        #             Message mismatch: published to DIRECT, queue expected TOPIC.
        # SYMPTOMS: No errors raised (publish succeeded), but queue.get() timed out because
        #           message was routed to wrong exchange type or dropped entirely.
        # SOLUTION: Explicitly construct RabbitExchange object with type=ExchangeType.TOPIC
        #           and durable=True when initializing from string. This ensures publish()
        #           uses the correct exchange type that matches test queue bindings.
        # DECISION: Make exchange type explicit rather than relying on FastStream defaults.
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
