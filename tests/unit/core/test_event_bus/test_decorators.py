"""Tests for event bus decorator syntax."""

import pytest

from messaging.core.contracts import BaseEvent
from messaging.core.contracts.event_bus import EventBus
from tests.unit.core.test_event_bus.test_fixtures import ExampleEvent


@pytest.mark.asyncio
async def test_event_bus_decorator_registers_async_subscribers() -> None:
    """Decorators should register async callbacks without handler classes."""
    seen: list[int] = []
    event_bus = EventBus()

    @event_bus.subscriber(ExampleEvent)
    async def capture(event: BaseEvent) -> None:
        seen.append(event.xp_delta)  # type: ignore[attr-defined] # xp_delta is dynamically added test attribute

    await event_bus.dispatch(ExampleEvent(xp_delta=20))

    assert seen == [20]
