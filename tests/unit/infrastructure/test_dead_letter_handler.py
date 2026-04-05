"""Unit tests for DeadLetterHandler routing behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest

from messaging.infrastructure.pubsub.dead_letter_handler import DeadLetterHandler
from tests.unit.infrastructure.conftest import ExampleEvent, FakePublisher, FakeRepository


@pytest.mark.asyncio
async def test_handle_routes_to_dlq_topic() -> None:
    """Handle should mark event as failed and publish to eventType.DLQ topic."""
    repository = FakeRepository()
    dlq_publisher = FakePublisher()
    handler = DeadLetterHandler(repository, cast(Any, dlq_publisher))
    event = ExampleEvent(xp_delta=10, occurred_at=datetime(2026, 3, 30, tzinfo=UTC))

    await handler.handle(event, "timeout error")

    assert repository.failed == [(event.event_id, "timeout error")]
    assert dlq_publisher.topics == [f"{event.event_type}.DLQ"]
    assert len(dlq_publisher.messages) == 1
    assert dlq_publisher.messages[0]["error"] == "timeout error"


@pytest.mark.asyncio
async def test_handle_preserves_event_in_dlq_message() -> None:
    """DLQ message should contain original event data."""
    repository = FakeRepository()
    dlq_publisher = FakePublisher()
    handler = DeadLetterHandler(repository, cast(Any, dlq_publisher))
    event = ExampleEvent(xp_delta=42)

    await handler.handle(event, "serialization failed")

    dlq_message = dlq_publisher.messages[0]
    assert "event" in dlq_message
    assert dlq_message["event"]["eventType"] == event.event_type
