"""Handler name resolution for event bus registrations.

This module provides utilities for extracting handler names and callbacks
from handler instances or raw async functions.

See Also
--------
- messaging.core.contracts.bus.event_bus : The EventBus that uses this resolver
- messaging.core.contracts.bus.types : Handler type definitions
"""

from __future__ import annotations

from messaging.core.contracts.bus.types import EventCallback, HandlerLike


class HandlerResolver:
    """Resolve handler names and callbacks from handler instances or functions."""

    @staticmethod
    def resolve_name(handler: HandlerLike) -> str:
        """Extract handler name from class or function.

        Args:
            handler (HandlerLike): Handler instance (with .handle method) or async callback

        Returns:
            str: Class name for handler instances, function name for callbacks.
        """
        if hasattr(handler, "handle"):
            return handler.__class__.__name__
        return handler.__name__

    @staticmethod
    def extract_callback(handler: HandlerLike) -> EventCallback:
        """Extract callable from handler instance or return callback directly.

        Args:
            handler (HandlerLike): Handler instance (with .handle method) or async callback

        Returns:
            EventCallback: The async callable that will be invoked for events.
        """
        return handler.handle if hasattr(handler, "handle") else handler
