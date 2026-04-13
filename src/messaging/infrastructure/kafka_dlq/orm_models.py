"""ORM models for Kafka dead-letter queue."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from messaging.infrastructure.persistence.orm_models.orm_base import Base

# LINTER EXCLUSION (PF002): Suppressed in setup.cfg for this file
# RATIONALE: This is a SQLAlchemy ORM model using Mapped[] syntax, NOT a Pydantic model.
#            mapped_column(default=...) is SQLAlchemy's column default syntax.
#            Pydantic's Field() is incompatible with SQLAlchemy's declarative base.
#            flake8-pydantic incorrectly flags SQLAlchemy Mapped[] defaults as violations.


class FailedKafkaMessage(Base):
    """Failed Kafka message stored in DLQ."""

    __tablename__ = "failed_kafka_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="failed", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
