"""Persistence layer for outbox and idempotency tracking.

This module provides SQLAlchemy-based persistence for:

**Outbox Pattern**
  - OutboxEventRecord : ORM model for unpublished events
  - Stores events atomically with business data in same transaction

**Consumer Idempotency**
  - ProcessedMessageRecord : ORM model for consumed message tracking
  - SqlAlchemyProcessedMessageStore : Deduplication store for consumers
  - Prevents duplicate processing on Kafka replay

**Session Management**
  - create_session_factory : Async SQLAlchemy session configuration

See Also
--------
- eventing.infrastructure.outbox : Outbox repository and worker
- eventing.infrastructure.messaging : Kafka consumer base with idempotency
"""

from eventing.infrastructure.persistence.outbox_orm import OutboxEventRecord
from eventing.infrastructure.persistence.processed_message_orm import ProcessedMessageRecord
from eventing.infrastructure.persistence.processed_message_store import (
    SqlAlchemyProcessedMessageStore,
)
from eventing.infrastructure.persistence.session import create_session_factory

__all__ = [
    "OutboxEventRecord",
    "ProcessedMessageRecord",
    "SqlAlchemyProcessedMessageStore",
    "create_session_factory",
]
