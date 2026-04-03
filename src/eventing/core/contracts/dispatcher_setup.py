"""Helpers for wiring the in-process event dispatcher.

This module provides factory functions like `build_event_bus` and data structures
like `HandlerRegistration` to easily configure and instantiate event buses with
pre-wired handlers.

See also
--------
- eventing.core.contracts.bus.event_bus : The event bus created by these factories
"""

from __future__ import annotations

from dataclasses import dataclass

from eventing.core.contracts.base_event import BaseEvent
from eventing.core.contracts.bus import DispatchBackend, EventBus
from eventing.core.contracts.dispatch_hooks import DispatchHooks, DispatchSettings
from python_domain_events import IDomainEventHandler, InProcessEventDispatcher


@dataclass(frozen=True, slots=True)
class HandlerRegistration:
    """Bind an event class to an in-process handler instance."""

    event_type: type[BaseEvent]
    handler: IDomainEventHandler[BaseEvent]


def build_dispatcher(registrations: list[HandlerRegistration]) -> InProcessEventDispatcher:
    """Create a dispatcher and register all provided handlers."""
    dispatcher = InProcessEventDispatcher()
    for registration in registrations:
        dispatcher.register(registration.event_type, registration.handler)
    return dispatcher


def build_event_bus(
    registrations: list[HandlerRegistration],
    *,
    backend: DispatchBackend | None = None,
    hooks: DispatchHooks | None = None,
    settings: DispatchSettings | None = None,
) -> EventBus:
    """Create the higher-level event bus from the same registration model."""
    event_bus = EventBus(backend=backend, hooks=hooks, settings=settings)
    for registration in registrations:
        event_bus.register(registration.event_type, registration.handler)
    return event_bus
