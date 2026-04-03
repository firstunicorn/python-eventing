"""Unit tests for eventing core event contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eventing.core.contracts import (
    BaseEvent,
    EventEnvelopeFormatter,
    EventRegistry,
    HandlerRegistration,
    UnknownEventTypeError,
    build_dispatcher,
)
from python_domain_events import IDomainEventHandler


class ExampleEvent(BaseEvent):
    """Concrete test event used for contract verification."""

    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "user-123"
    source: str = "gamification-service"
    xp_delta: int


class RecordingHandler(IDomainEventHandler[BaseEvent]):
    """Capture dispatched events for assertion."""

    def __init__(self) -> None:
        self.seen: list[BaseEvent] = []

    async def handle(self, event: BaseEvent) -> None:
        self.seen.append(event)


def test_base_event_serializes_with_camel_case() -> None:
    """Base events should emit JSON-ready payloads with aliases."""
    event = ExampleEvent(xp_delta=15)

    assert event.to_message()["eventType"] == "gamification.XPAwarded"
    assert event.get_partition_key() == "user-123"


def test_base_event_requires_timezone_aware_timestamp() -> None:
    """Naive timestamps should be rejected."""
    with pytest.raises(ValueError, match="timezone-aware"):
        ExampleEvent(xp_delta=10, occurred_at=datetime(2026, 3, 30, 8, 0, 0))


def test_event_registry_round_trips_payloads() -> None:
    """Registry should resolve and deserialize registered event payloads."""
    event = ExampleEvent(xp_delta=20, occurred_at=datetime(2026, 3, 30, tzinfo=UTC))
    registry = EventRegistry()
    registry.register(ExampleEvent)

    deserialized = registry.deserialize(event.to_message())

    assert isinstance(deserialized, ExampleEvent)
    assert deserialized.xp_delta == 20


def test_event_registry_raises_for_unknown_types() -> None:
    """Unknown event types should fail loudly."""
    registry = EventRegistry()

    with pytest.raises(UnknownEventTypeError):
        registry.get("missing.event")


@pytest.mark.asyncio
async def test_dispatcher_routes_registered_handlers() -> None:
    """Dispatcher should invoke handlers bound to an event class."""
    handler = RecordingHandler()
    dispatcher = build_dispatcher([HandlerRegistration(ExampleEvent, handler)])
    event = ExampleEvent(xp_delta=25)

    await dispatcher.dispatch(event)

    assert handler.seen == [event]


def test_event_envelope_formats_cloud_events() -> None:
    """CloudEvents formatting should preserve key event metadata."""
    event = ExampleEvent(xp_delta=30)
    formatter = EventEnvelopeFormatter()

    envelope = formatter.format(event)

    assert envelope["id"] == str(event.event_id)
    assert envelope["type"] == "gamification.XPAwarded"
    assert envelope["source"] == "gamification-service"
    assert envelope["data"]["xpDelta"] == 30
