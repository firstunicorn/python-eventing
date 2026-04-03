"""SQLAlchemy ORM model for durable consumer idempotency."""

# pylint: disable=too-many-ancestors

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from eventing.infrastructure.persistence.orm_base import Base


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
