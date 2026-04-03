"""Processed-message store contract for durable consumer idempotency.

This module defines `IProcessedMessageStore`, an interface for tracking which
events have been processed by specific consumers. Implementations of this protocol
ensure that consumer event handlers are idempotent, even if the underlying message
broker (e.g., Kafka) delivers the same message multiple times.

See also
--------
- eventing.infrastructure.messaging.kafka_consumer_base : The consumer base class that uses this
- eventing.infrastructure.persistence.processed_message_store : The SQLAlchemy implementation
"""

from __future__ import annotations

from typing import Protocol


class IProcessedMessageStore(Protocol):
    """Claim inbound event identifiers for one named consumer."""

    async def claim(self, *, consumer_name: str, event_id: str) -> bool:
        """Return whether this consumer may process the given event identifier."""
