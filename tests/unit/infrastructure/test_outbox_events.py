"""Unit tests for outbox event handler."""

from __future__ import annotations

import pytest

from messaging.infrastructure.outbox import OutboxEventHandler
from tests.unit.infrastructure.conftest import ExampleEvent, FakeRepository


@pytest.mark.asyncio
async def test_outbox_event_handler_persists_event() -> None:
    """Outbox handler should store dispatched events."""
    repository = FakeRepository()
    handler = OutboxEventHandler(repository)
    event = ExampleEvent(xp_delta=10)

    await handler.handle(event)

    assert repository.added == [event]
