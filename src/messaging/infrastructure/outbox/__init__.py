"""Transactional outbox pattern implementation.

The outbox pattern ensures reliable event publishing by storing events
in the application database within the same transaction as business data,
then publishing them asynchronously to Kafka.

**Core components**
  - OutboxEventHandler : Store events in outbox during transaction
  - SqlAlchemyOutboxRepository : CRUD operations on outbox table
  - ScheduledOutboxWorker : Background worker that publishes unpublished events
  - build_outbox_config : Factory for outbox configuration

**Guarantees**
  - At-least-once delivery (events never lost, may be duplicated)
  - Ordered publication per aggregate (events publish in insert order)
  - Survives app crashes (unpublished events persist in database)

**Usage pattern**
  1. Register OutboxEventHandler as domain event listener
  2. Emit domain events in application transaction
  3. Events automatically save to outbox_events table
  4. OutboxWorker polls table and publishes to Kafka
  5. Published events marked as published_at timestamp

See also
--------
- messaging.core : Domain event definitions
- messaging.infrastructure.messaging : KafkaEventPublisher used by worker
- messaging.infrastructure.persistence : OutboxEventRecord ORM model
"""

from messaging.infrastructure.outbox.outbox_config import build_outbox_config
from messaging.infrastructure.outbox.outbox_event_handler import OutboxEventHandler
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from messaging.infrastructure.outbox.outbox_worker import ScheduledOutboxWorker

__all__ = [
    "OutboxEventHandler",
    "ScheduledOutboxWorker",
    "SqlAlchemyOutboxRepository",
    "build_outbox_config",
]
