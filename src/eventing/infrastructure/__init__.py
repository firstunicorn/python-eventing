"""Infrastructure implementations for event persistence and messaging.

This layer provides concrete implementations of technical concerns:

**Transactional Outbox**
  - OutboxEventHandler : Persist events in application transaction
  - SqlAlchemyOutboxRepository : Outbox table operations
  - ScheduledOutboxWorker : Background publisher for unpublished events

**Kafka Integration**
  - KafkaEventPublisher : Publish events to Kafka topics
  - IdempotentConsumerBase : Replay-safe consumer with deduplication
  - DeadLetterHandler : Route failures to DLQ

**Persistence**
  - OutboxEventRecord, ProcessedMessageRecord : SQLAlchemy ORM models
  - SqlAlchemyProcessedMessageStore : Consumer idempotency tracking
  - create_session_factory : Async session configuration

**Health Checks**
  - EventingHealthCheck : Outbox staleness monitoring

See also
--------
- eventing.core : Domain-agnostic event contracts
- eventing.infrastructure.outbox : Outbox pattern implementation
- eventing.infrastructure.messaging : Kafka adapters
- eventing.infrastructure.persistence : Database models and stores
"""

from eventing.infrastructure.health import EventingHealthCheck
from eventing.infrastructure.messaging import (
    DeadLetterHandler,
    IdempotentConsumerBase,
    IProcessedMessageStore,
    KafkaEventPublisher,
    create_kafka_broker,
)
from eventing.infrastructure.outbox import (
    OutboxEventHandler,
    ScheduledOutboxWorker,
    SqlAlchemyOutboxRepository,
    build_outbox_config,
)
from eventing.infrastructure.persistence import (
    OutboxEventRecord,
    ProcessedMessageRecord,
    SqlAlchemyProcessedMessageStore,
    create_session_factory,
)

__all__ = [
    "DeadLetterHandler",
    "EventingHealthCheck",
    "IProcessedMessageStore",
    "IdempotentConsumerBase",
    "KafkaEventPublisher",
    "OutboxEventHandler",
    "OutboxEventRecord",
    "ProcessedMessageRecord",
    "ScheduledOutboxWorker",
    "SqlAlchemyOutboxRepository",
    "SqlAlchemyProcessedMessageStore",
    "build_outbox_config",
    "create_kafka_broker",
    "create_session_factory",
]
