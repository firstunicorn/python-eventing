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
- messaging.infrastructure.outbox : Outbox repository and worker
- messaging.infrastructure.messaging : Kafka consumer base with idempotency
"""

from messaging.infrastructure.persistence.orm_models.outbox_orm import OutboxEventRecord
from messaging.infrastructure.persistence.orm_models.processed_message_orm import (
    ProcessedMessageRecord,
)
from messaging.infrastructure.persistence.processed_message_store.claim_helpers import (
    build_claim_statement,
    is_duplicate_claim,
)
from messaging.infrastructure.persistence.processed_message_store.processed_message_store import (
    SqlAlchemyProcessedMessageStore,
)
from messaging.infrastructure.persistence.session import create_session_factory

__all__ = [
    "OutboxEventRecord",
    "ProcessedMessageRecord",
    "SqlAlchemyProcessedMessageStore",
    "build_claim_statement",
    "create_session_factory",
    "is_duplicate_claim",
]
