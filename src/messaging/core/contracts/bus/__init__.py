"""Event bus facade and dispatch backend abstractions.

The event bus provides a decorator-style API for subscriber registration
with pluggable dispatch backends, hooks, and tracing.

Key Classes
-----------
EventBus
    High-level facade for decorator-style registration, dispatch hooks,
    and backend-agnostic event routing.

DispatchBackend
    Abstract interface for dispatch strategies. Implementations control
    how events are routed to handlers (sequential, parallel, etc.).

SequentialDispatchBackend
    Default backend that dispatches events to handlers one at a time.

See also
--------
- messaging.core.contracts.dispatch_hooks : Hook definitions and settings
- messaging.core.contracts.dispatcher_setup : Mediator integration
"""

from messaging.core.contracts.bus.backends import DispatchBackend, SequentialDispatchBackend
from messaging.core.contracts.bus.event_bus import EventBus
from messaging.core.contracts.bus.types import EventCallback, HandlerLike, RegisteredHandler

__all__ = [
    "DispatchBackend",
    "EventBus",
    "EventCallback",
    "HandlerLike",
    "RegisteredHandler",
    "SequentialDispatchBackend",
]
