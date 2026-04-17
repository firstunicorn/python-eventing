"""Canonical event base shared across in-process and outbox flows.

This module defines the foundational `BaseEvent` class that all domain
events must inherit from. It provides common fields like event ID,
timestamps, and tracking identifiers.

See Also
--------
- messaging.core.contracts.event_registry : For registering event types
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from python_domain_events import BaseDomainEvent
from python_outbox_core import IOutboxEvent
from messaging.catalog.manager import EventCatalogManager
from messaging.config.event_catalog_settings import EventCatalogSettings

logger = logging.getLogger(__name__)

# Global catalog manager (initialized once at module load)
_catalog_settings = EventCatalogSettings()
_catalog_manager = (
    EventCatalogManager(_catalog_settings) if _catalog_settings.repo_url else None
)


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

    @field_validator("event_type")
    @classmethod
    def validate_event_type_format(cls, value: str) -> str:
        """Validate event type format and against catalog.

        Layer 1: Format validation (domain.entity.event pattern)
        Layer 2: Catalog validation (if catalog configured)
        """
        # Layer 1: Format validation
        pattern = r"^[a-z]+\.[a-z-]+\.[a-z-]+$"
        if not re.match(pattern, value):
            msg = (
                f"event_type must match pattern: domain.entity.event\n"
                f"Expected: lowercase with dots (e.g., orders.order.created)\n"
                f"Got: {value}"
            )
            raise ValueError(msg)

        # Layer 2: Catalog validation
        if _catalog_manager:
            # Check if there's a running event loop
            try:
                asyncio.get_running_loop()
                # We're in an async context, need to create_task or run_coroutine_threadsafe
                # For Pydantic validators, we can't await, so we check catalog_data directly
                if _catalog_manager._catalog_data:
                    is_valid, message = _catalog_manager.validate_event_type(value)
                    if not is_valid:
                        raise ValueError(message)
                    if "Warning" in message:
                        logger.warning(message)
            except RuntimeError:
                # No running loop, safe to use asyncio.run()
                catalog = asyncio.run(_catalog_manager.ensure_catalog())
                if catalog:
                    is_valid, message = _catalog_manager.validate_event_type(value)
                    if not is_valid:
                        raise ValueError(message) from None
                    if "Warning" in message:
                        logger.warning(message)

        return value

    @field_validator("source")
    @classmethod
    def validate_source_format(cls, value: str) -> str:
        """Validate source format and against catalog.

        Layer 1: Format validation (lowercase-with-hyphens pattern)
        Layer 2: Catalog validation (if catalog configured)
        """
        # Layer 1: Format validation
        pattern = r"^[a-z][a-z0-9-]*$"
        if not re.match(pattern, value):
            msg = (
                f"source must be lowercase-with-hyphens\n"
                f"Expected: lowercase, hyphens, numbers (e.g., order-service)\n"
                f"Got: {value}"
            )
            raise ValueError(msg)

        # Layer 2: Catalog validation
        if _catalog_manager:
            # Check if there's a running event loop
            try:
                asyncio.get_running_loop()
                # We're in an async context, check catalog_data directly
                if _catalog_manager._catalog_data:
                    is_valid, message = _catalog_manager.validate_service_name(value)
                    if not is_valid:
                        raise ValueError(message)
                    if "Warning" in message:
                        logger.warning(message)
            except RuntimeError:
                # No running loop, safe to use asyncio.run()
                catalog = asyncio.run(_catalog_manager.ensure_catalog())
                if catalog:
                    is_valid, message = _catalog_manager.validate_service_name(value)
                    if not is_valid:
                        raise ValueError(message) from None
                    if "Warning" in message:
                        logger.warning(message)

        return value

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
