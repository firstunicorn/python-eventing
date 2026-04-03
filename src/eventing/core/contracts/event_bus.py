"""Event bus facade backward compatibility exports.

This module provides legacy imports for the event-bus facade internals.
The actual implementation lives in the ``eventing.core.contracts.bus`` package.

See also
--------
- eventing.core.contracts.bus : Actual event bus implementations
"""

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
