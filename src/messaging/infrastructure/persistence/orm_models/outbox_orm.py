"""SQLAlchemy ORM model for transactional outbox storage.

This module defines `OutboxEventRecord`, which represents a domain event stored
in the database waiting to be published to Kafka. It includes fields for the
event payload, metadata, and tracking columns for publication status.

See Also
--------
- messaging.infrastructure.outbox.outbox_repository : The repository that manages these records
"""

# pylint: disable=too-many-ancestors

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from messaging.infrastructure.persistence.orm_models.orm_base import Base


class OutboxEventRecord(Base):
    """Persisted event waiting to be published to Kafka."""

    __tablename__ = "outbox_events"
    __table_args__ = (Index("idx_outbox_unpublished", "published", "created_at"),)

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
