"""Eventing core event contracts and helpers."""

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
