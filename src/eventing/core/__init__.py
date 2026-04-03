"""Core cross-layer primitives for the eventing service."""

from eventing.core.contracts import (
    BaseEvent,
    DispatchBackend,
    DispatchHooks,
    DispatchSettings,
    DispatchTrace,
    EventBus,
    EventEnvelopeFormatter,
    EventRegistry,
    HandlerRegistration,
    SequentialDispatchBackend,
    UnknownEventTypeError,
    build_dispatcher,
    build_event_bus,
)

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
