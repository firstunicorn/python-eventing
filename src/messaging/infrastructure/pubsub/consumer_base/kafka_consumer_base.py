"""Idempotent consumer base backed by a durable processed-message store.

This module provides `IdempotentConsumerBase`, an abstract base class for Kafka
consumers that ensures each event is processed exactly once. It extracts the
`event_id` from incoming messages and attempts to claim it via the configured
processed message store before delegating to `handle_event`.

See Also
--------
- messaging.infrastructure.pubsub.consumer_validators : Event_id and name validation
- messaging.infrastructure.pubsub.consumer_consume : Consume method implementation
- messaging.infrastructure.pubsub.processed_message_store : The idempotency store protocol
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from messaging.infrastructure.pubsub.consumer_base.consumer_consume import consume_event
from messaging.infrastructure.pubsub.consumer_base.consumer_validators import validate_consumer_name
from messaging.infrastructure.pubsub.processed_message_store import IProcessedMessageStore


class IdempotentConsumerBase(ABC):
    """Skip duplicate events by identifier using a durable processed-message store."""

    def __init__(
        self,
        *,
        consumer_name: str,
        processed_message_store: IProcessedMessageStore,
    ) -> None:
        self._consumer_name = validate_consumer_name(consumer_name)
        self._processed_message_store = processed_message_store

    async def consume(self, message: dict[str, Any]) -> bool:
        """Process a message once, delegating to consume_event helper."""
        return await consume_event(
            message=message,
            consumer_name=self._consumer_name,
            processed_message_store=self._processed_message_store,
            handle_event_coro=self.handle_event,
        )

    @abstractmethod
    async def handle_event(self, message: dict[str, Any]) -> None:
        """Handle one deserialized event payload."""
