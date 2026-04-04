"""Core event contracts and dispatch primitives.

This module provides domain-agnostic event infrastructure:

- **BaseEvent** : Base class for all domain events with CloudEvents fields
- **EventRegistry** : Type-safe event schema registration
- **EventBus** : Decorator-style subscriber registration with hooks
- **EventEnvelopeFormatter** : CloudEvents 1.0 envelope wrapper

The core layer is framework-agnostic and can be used without infrastructure
dependencies for pure in-process event dispatch.

Examples
--------
>>> from messaging.core import BaseEvent, EventBus
>>>
>>> class OrderPlaced(BaseEvent):
...     event_type: str = "order.placed"
...     order_id: int
>>>
>>> bus = EventBus()
>>>
>>> @bus.subscriber(OrderPlaced)
>>> async def on_order(event: OrderPlaced):
...     print(f"Order {event.order_id} placed")
"""

from messaging.core.contracts import (
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
