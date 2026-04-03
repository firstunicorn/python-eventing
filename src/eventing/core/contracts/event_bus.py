"""Compatibility exports for the event-bus facade internals."""

from eventing.core.contracts.bus import (
    DispatchBackend,
    EventBus,
    RegisteredHandler,
    SequentialDispatchBackend,
)

__all__ = [
    "DispatchBackend",
    "EventBus",
    "RegisteredHandler",
    "SequentialDispatchBackend",
]
