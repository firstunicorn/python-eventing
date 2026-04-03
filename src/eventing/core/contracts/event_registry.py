"""Registry for mapping event type identifiers to event classes.

This module provides the `EventRegistry` which acts as a central catalog
for all domain events. It handles type-safe deserialization by mapping string
event types (e.g., "user.created") back to their corresponding Python classes.

See also
--------
- eventing.core.contracts.base_event : The base class for registered events
"""

from __future__ import annotations

from typing import Any

from pydantic_core import PydanticUndefined

from eventing.core.contracts.base_event import BaseEvent


class UnknownEventTypeError(KeyError):  # pylint: disable=too-many-ancestors
    """Raised when an event type cannot be resolved by the registry."""


class EventRegistry:
    """Store event type to model mappings for deserialization."""

    def __init__(self) -> None:
        self._event_types: dict[str, type[BaseEvent]] = {}

    def register(self, event_class: type[BaseEvent], *, event_type: str | None = None) -> None:
        """Register an event class by explicit or model-declared event type."""
        resolved_type = event_type or self._resolve_event_type(event_class)
        self._event_types[resolved_type] = event_class

    def register_many(self, event_classes: list[type[BaseEvent]]) -> None:
        """Register multiple event classes in insertion order."""
        for event_class in event_classes:
            self.register(event_class)

    def get(self, event_type: str) -> type[BaseEvent]:
        """Return the registered event class for the given type."""
        try:
            return self._event_types[event_type]
        except KeyError as error:
            raise UnknownEventTypeError(event_type) from error

    def deserialize(self, payload: dict[str, Any]) -> BaseEvent:
        """Build an event instance from a serialized payload."""
        event_type = payload.get("event_type") or payload.get("eventType")
        if not event_type:
            msg = "Payload must include event_type or eventType"
            raise UnknownEventTypeError(msg)
        return self.get(event_type).model_validate(payload)

    @staticmethod
    def _resolve_event_type(event_class: type[BaseEvent]) -> str:
        field = event_class.model_fields["event_type"]
        if field.default is PydanticUndefined:
            msg = f"{event_class.__name__} must declare a default event_type to auto-register"
            raise ValueError(msg)
        return str(field.default)
