"""Unit tests for the higher-level event bus facade."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest

from eventing.core.contracts import (
    BaseEvent,
    DispatchHooks,
    DispatchSettings,
    HandlerRegistration,
    SequentialDispatchBackend,
    build_event_bus,
)
from eventing.core.contracts.event_bus import DispatchBackend, EventBus, RegisteredHandler
from python_domain_events import IDomainEventHandler


class ExampleEvent(BaseEvent):
    """Concrete event for event-bus tests."""

    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "user-123"
    source: str = "gamification-service"
    xp_delta: int


class RecordingHandler(IDomainEventHandler[BaseEvent]):
    """Collect dispatched events."""

    def __init__(self) -> None:
        self.seen: list[BaseEvent] = []

    async def handle(self, event: BaseEvent) -> None:
        self.seen.append(event)


class ReversingBackend:
    """Custom backend used to prove backend abstraction works."""

    name = "reversing"

    def __init__(self) -> None:
        self.seen_handlers: list[list[str]] = []

    async def invoke(
        self,
        event: BaseEvent,
        handlers: list[RegisteredHandler],
        invoke_one: Callable[[RegisteredHandler], Awaitable[None]],
    ) -> None:
        _ = event
        self.seen_handlers.append([handler.name for handler in handlers])
        for handler in reversed(handlers):
            await invoke_one(handler)


@pytest.mark.asyncio
async def test_event_bus_builds_from_handler_registrations() -> None:
    """The facade should reuse the existing registration shape."""
    handler = RecordingHandler()
    event_bus = build_event_bus([HandlerRegistration(ExampleEvent, handler)])
    event = ExampleEvent(xp_delta=15)

    await event_bus.dispatch(event)

    assert handler.seen == [event]


@pytest.mark.asyncio
async def test_event_bus_decorator_registers_async_subscribers() -> None:
    """Decorators should register async callbacks without handler classes."""
    seen: list[int] = []
    event_bus = EventBus()

    @event_bus.subscriber(ExampleEvent)
    async def capture(event: BaseEvent) -> None:
        seen.append(event.xp_delta)  # type: ignore[attr-defined]

    await event_bus.dispatch(ExampleEvent(xp_delta=20))

    assert seen == [20]


@pytest.mark.asyncio
async def test_event_bus_exposes_global_success_and_failure_hooks() -> None:
    """Lifecycle hooks should expose handler-level dispatch outcomes."""
    traces: list[tuple[str, str | None]] = []
    event_bus = EventBus(
        hooks=DispatchHooks(
            on_dispatch=lambda trace: traces.append((trace.stage, trace.handler_name)),
            on_success=lambda trace: traces.append((trace.stage, trace.handler_name)),
            on_failure=lambda trace: traces.append((trace.stage, trace.handler_name)),
        )
    )

    @event_bus.subscriber(ExampleEvent, handler_name="ok-handler")
    async def succeed(event: BaseEvent) -> None:
        _ = event

    @event_bus.subscriber(ExampleEvent, handler_name="boom-handler")
    async def fail(event: BaseEvent) -> None:
        _ = event
        msg = "boom"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="boom"):
        await event_bus.dispatch(ExampleEvent(xp_delta=30))

    assert traces == [
        ("dispatch", "ok-handler"),
        ("success", "ok-handler"),
        ("dispatch", "boom-handler"),
        ("failure", "boom-handler"),
    ]


@pytest.mark.asyncio
async def test_event_bus_debug_and_disable_hooks_are_explicit() -> None:
    """Disabled dispatch should skip handlers and still emit debug traces."""
    disabled: list[str] = []
    debug: list[str] = []
    event_bus = EventBus(
        hooks=DispatchHooks(
            on_disabled=lambda trace: disabled.append(trace.stage),
            on_debug=lambda trace: debug.append(trace.stage),
        ),
        settings=DispatchSettings(enabled=False, debug=True),
    )

    await event_bus.dispatch(ExampleEvent(xp_delta=35))

    assert disabled == ["disabled"]
    assert debug == ["disabled"]


@pytest.mark.asyncio
async def test_event_bus_allows_custom_backends() -> None:
    """Backends should control handler execution order."""
    seen: list[str] = []
    backend = ReversingBackend()
    event_bus = EventBus(backend=backend)

    @event_bus.subscriber(ExampleEvent, handler_name="first")
    async def first(event: BaseEvent) -> None:
        _ = event
        seen.append("first")

    @event_bus.subscriber(ExampleEvent, handler_name="second")
    async def second(event: BaseEvent) -> None:
        _ = event
        seen.append("second")

    await event_bus.dispatch(ExampleEvent(xp_delta=40))

    assert backend.seen_handlers == [["first", "second"]]
    assert seen == ["second", "first"]


def test_sequential_dispatch_backend_has_stable_name() -> None:
    """The default backend should expose a predictable identifier."""
    backend: DispatchBackend = SequentialDispatchBackend()
    assert SequentialDispatchBackend().name == "sequential"
    assert backend.name == "sequential"
