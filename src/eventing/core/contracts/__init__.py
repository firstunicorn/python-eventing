"""Event contracts, registry, and dispatch patterns.

This package defines the core eventing contracts:

**Event Definitions**
  - BaseEvent : Canonical event schema with CloudEvents fields
  - EventRegistry : Type registry for event deserialization

**Dispatch Patterns**
  - EventBus : High-level decorator-style API with hooks
  - build_dispatcher : Mediator-based command/event routing
  - build_event_bus : Factory for pre-configured event bus

**Envelope Formatting**
  - EventEnvelopeFormatter : CloudEvents 1.0 wrapper for Kafka

See Also
--------
- eventing.core.contracts.bus : Event bus facade and dispatch backends
- eventing.infrastructure.outbox : Transactional outbox handler
"""

from eventing.core.contracts.base_event import BaseEvent
from eventing.core.contracts.bus import DispatchBackend, EventBus, SequentialDispatchBackend
from eventing.core.contracts.dispatch_hooks import DispatchHooks, DispatchSettings, DispatchTrace
from eventing.core.contracts.dispatcher_setup import (
    HandlerRegistration,
    build_dispatcher,
    build_event_bus,
)
from eventing.core.contracts.event_envelope import EventEnvelopeFormatter
from eventing.core.contracts.event_registry import EventRegistry, UnknownEventTypeError

__all__ = [
    "BaseEvent",
    "DispatchBackend",
    "DispatchHooks",
    "DispatchSettings",
    "DispatchTrace",
    "EventBus",
    "EventEnvelopeFormatter",
    "EventRegistry",
    "HandlerRegistration",
    "SequentialDispatchBackend",
    "UnknownEventTypeError",
    "build_dispatcher",
    "build_event_bus",
]
