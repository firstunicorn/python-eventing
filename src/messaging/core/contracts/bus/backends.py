"""Dispatch backend abstractions for the event bus facade.

This module provides the `DispatchBackend` protocol and the default
`SequentialDispatchBackend` implementation. Backends control how the event bus
routes events to their registered handlers (e.g., sequentially, concurrently).

See also
--------
- messaging.core.contracts.bus.event_bus : The event bus that uses these backends
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from messaging.core.contracts.base_event import BaseEvent
from messaging.core.contracts.bus.types import RegisteredHandler


class DispatchBackend(Protocol):
    """Execute one dispatch strategy."""

    name: str

    async def invoke(
        self,
        event: BaseEvent,
        handlers: list[RegisteredHandler],
        invoke_one: Callable[[RegisteredHandler], Awaitable[None]],
    ) -> None:
        """Run the provided handlers for one event."""


class SequentialDispatchBackend:
    """Dispatch handlers sequentially in registration order."""

    name = "sequential"

    async def invoke(
        self,
        event: BaseEvent,
        handlers: list[RegisteredHandler],
        invoke_one: Callable[[RegisteredHandler], Awaitable[None]],
    ) -> None:
        _ = event
        for handler in handlers:
            await invoke_one(handler)
