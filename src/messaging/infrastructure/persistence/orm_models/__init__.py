"""ORM model classes.

Re-exports the SQLAlchemy ORM model definitions for the outbox and
processed-message record tables.
"""

from messaging.infrastructure.persistence.orm_models.orm_base import Base
from messaging.infrastructure.persistence.orm_models.outbox_orm import OutboxEventRecord
from messaging.infrastructure.persistence.orm_models.processed_message_orm import (
    ProcessedMessageRecord,
)

__all__ = [
    "Base",
    "OutboxEventRecord",
    "ProcessedMessageRecord",
]
