"""Unit tests for durable consumer idempotency behavior."""

from __future__ import annotations

from typing import Any

import pytest

from eventing.infrastructure.messaging import IProcessedMessageStore, IdempotentConsumerBase


class FakeProcessedMessageStore(IProcessedMessageStore):
    """Store fake that tracks claimed event identifiers by consumer."""

    def __init__(self) -> None:
        self._claims: set[tuple[str, str]] = set()

    async def claim(self, *, consumer_name: str, event_id: str) -> bool:
        claim = (consumer_name, event_id)
        if claim in self._claims:
            return False
        self._claims.add(claim)
        return True


class RecordingConsumer(IdempotentConsumerBase):
    """Consumer fake that records handled messages."""

    def __init__(self, consumer_name: str, processed_message_store: IProcessedMessageStore) -> None:
        super().__init__(
            consumer_name=consumer_name,
            processed_message_store=processed_message_store,
        )
        self.handled: list[dict[str, Any]] = []

    async def handle_event(self, message: dict[str, Any]) -> None:
        self.handled.append(message)


@pytest.mark.asyncio
async def test_idempotent_consumer_skips_duplicates_per_consumer() -> None:
    """Consumer should process one event identifier only once per consumer name."""
    store = FakeProcessedMessageStore()
    consumer = RecordingConsumer("gamification.learning", store)
    message = {"eventId": "abc-123", "payload": 1}

    first = await consumer.consume(message)
    second = await consumer.consume(message)

    assert first is True
    assert second is False
    assert consumer.handled == [message]


@pytest.mark.asyncio
async def test_idempotent_consumer_allows_same_event_for_other_consumers() -> None:
    """Different consumers should be able to claim the same event identifier once each."""
    store = FakeProcessedMessageStore()
    first_consumer = RecordingConsumer("gamification.learning", store)
    second_consumer = RecordingConsumer("gamification.assessment", store)
    message = {"eventId": "abc-123", "payload": 1}

    assert await first_consumer.consume(message) is True
    assert await second_consumer.consume(message) is True


@pytest.mark.asyncio
async def test_idempotent_consumer_requires_event_identifier() -> None:
    """Malformed messages should fail fast when the event identifier is missing."""
    store = FakeProcessedMessageStore()
    consumer = RecordingConsumer("gamification.learning", store)

    with pytest.raises(ValueError, match="eventId or event_id"):
        await consumer.consume({"payload": 1})
