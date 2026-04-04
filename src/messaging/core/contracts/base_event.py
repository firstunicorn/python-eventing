"""Canonical event base shared across in-process and outbox flows.

This module defines the foundational `BaseEvent` class that all domain
events must inherit from. It provides common fields like event ID,
timestamps, and tracking identifiers.

See also
--------
- messaging.core.contracts.event_registry : For registering event types
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from python_domain_events import BaseDomainEvent
from python_outbox_core import IOutboxEvent


class BaseEvent(IOutboxEvent, BaseDomainEvent):  # pylint: disable=too-many-ancestors
    """Bridge event contract for internal dispatching and outbox publishing."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(min_length=3)
    aggregate_id: str = Field(min_length=1)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = Field(min_length=1)
    data_version: str = Field(default="1.0", min_length=1)
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at")
    @classmethod
    def ensure_utc_timestamp(cls, value: datetime) -> datetime:
        """Normalize event timestamps to UTC and reject naive datetimes."""
        _ = cls.__name__
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "occurred_at must be timezone-aware"
            raise ValueError(msg)
        return value.astimezone(UTC)

    def to_message(self) -> dict[str, Any]:
        """Serialize the event as a JSON-friendly payload."""
        return self.model_dump(mode="json", by_alias=True)

    def get_partition_key(self) -> str:
        """Use aggregate identity as the default broker partition key."""
        return self.aggregate_id
