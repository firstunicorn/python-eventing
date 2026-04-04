"""SQLAlchemy ORM model for durable consumer idempotency.

This module defines `ProcessedMessageRecord`, an ORM model used to track which
events have already been processed by specific consumers. It uses a composite
primary key of `(consumer_name, event_id)` to ensure an event is only processed
once per consumer group.

See also
--------
- messaging.infrastructure.persistence.processed_message_store : The store that manages these records
"""

# pylint: disable=too-many-ancestors

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from messaging.infrastructure.persistence.orm_models.orm_base import Base


class ProcessedMessageRecord(Base):
    """Persist one successfully claimed event identifier per consumer."""

    __tablename__ = "processed_messages"

    consumer_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
