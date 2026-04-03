"""Idempotent consumer base backed by a durable processed-message store."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from eventing.infrastructure.messaging.processed_message_store import IProcessedMessageStore


class IdempotentConsumerBase(ABC):
    """Skip duplicate events by identifier using a durable processed-message store."""

    def __init__(
        self,
        *,
        consumer_name: str,
        processed_message_store: IProcessedMessageStore,
    ) -> None:
        normalized_name = consumer_name.strip()
        if not normalized_name:
            msg = "consumer_name must not be empty"
            raise ValueError(msg)
        self._consumer_name = normalized_name
        self._processed_message_store = processed_message_store

    async def consume(self, message: dict[str, Any]) -> bool:
        """Process a message once, returning whether work was performed."""
        event_id = self._extract_event_id(message)
        claimed = await self._processed_message_store.claim(
            consumer_name=self._consumer_name,
            event_id=event_id,
        )
        if not claimed:
            return False
        await self.handle_event(message)
        return True

    @staticmethod
    def _extract_event_id(message: dict[str, Any]) -> str:
        raw_event_id = message.get("eventId") or message.get("event_id")
        if raw_event_id is None:
            msg = "message must include eventId or event_id"
            raise ValueError(msg)
        event_id = str(raw_event_id).strip()
        if not event_id:
            msg = "eventId must not be empty"
            raise ValueError(msg)
        return event_id

    @abstractmethod
    async def handle_event(self, message: dict[str, Any]) -> None:
        """Handle one deserialized event payload."""
