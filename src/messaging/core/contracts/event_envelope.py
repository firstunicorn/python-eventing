"""CloudEvents envelope formatting helpers.

This module provides a formatter to wrap domain events in the
CloudEvents 1.0 specification format before publishing to external systems.

See also
--------
- messaging.core.contracts.base_event : The event base class
"""

from __future__ import annotations

from typing import Any

from messaging.core.contracts.base_event import BaseEvent
from python_outbox_core import CloudEventsFormatter


class EventEnvelopeFormatter:
    """Format canonical events as CloudEvents 1.0 payloads."""

    def __init__(
        self,
        default_source: str | None = None,
        data_content_type: str = "application/json",
    ) -> None:
        self._default_source = default_source
        self._data_content_type = data_content_type

    def format(self, event: BaseEvent) -> dict[str, Any]:
        """Return a CloudEvents envelope for the given event."""
        formatter = CloudEventsFormatter(
            source=self._default_source or event.source,
            data_content_type=self._data_content_type,
        )
        return formatter.format(event)

    def get_content_type(self) -> str:
        """Return the content type produced by the underlying formatter."""
        formatter = CloudEventsFormatter(source=self._default_source or "eventing")
        return formatter.get_content_type()
