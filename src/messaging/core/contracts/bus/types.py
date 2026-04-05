"""Type aliases and lightweight records for event-bus dispatch.

This module defines the type hints and data structures used internally by
the `EventBus` to manage registered handlers and callbacks.

See Also
--------
- messaging.core.contracts.bus.event_bus : The main event bus implementation
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from messaging.core.contracts.base_event import BaseEvent
from python_domain_events import IDomainEventHandler

EventCallback = Callable[[BaseEvent], Awaitable[None]]
HandlerLike = IDomainEventHandler[BaseEvent] | EventCallback


@dataclass(frozen=True, slots=True)
class RegisteredHandler:
    """Store one registered callback with its display name."""

    name: str
    callback: EventCallback
