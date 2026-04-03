"""Processed-message store contract for durable consumer idempotency."""

from __future__ import annotations

from typing import Protocol


class IProcessedMessageStore(Protocol):
    """Claim inbound event identifiers for one named consumer."""

    async def claim(self, *, consumer_name: str, event_id: str) -> bool:
        """Return whether this consumer may process the given event identifier."""
