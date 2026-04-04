"""Event bus facade exports.

This module provides the main event-bus facade for the application.
The actual implementation lives in the ``messaging.core.contracts.bus`` package.

See also
--------
- messaging.core.contracts.bus : Actual event bus implementations
"""

from messaging.core.contracts.bus import (
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
