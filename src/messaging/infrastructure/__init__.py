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

See Also
--------
- messaging.core : Domain-agnostic event contracts
- messaging.infrastructure.outbox : Outbox pattern implementation
- messaging.infrastructure.messaging : Kafka adapters
- messaging.infrastructure.persistence : Database models and stores
"""

from messaging.infrastructure.health import EventingHealthCheck
from messaging.infrastructure.outbox import (
    OutboxEventHandler,
    ScheduledOutboxWorker,
    SqlAlchemyOutboxRepository,
    build_outbox_config,
)
from messaging.infrastructure.persistence import (
    OutboxEventRecord,
    ProcessedMessageRecord,
    SqlAlchemyProcessedMessageStore,
    create_session_factory,
)
from messaging.infrastructure.pubsub import (
    DeadLetterHandler,
    IdempotentConsumerBase,
    IProcessedMessageStore,
    KafkaEventPublisher,
    create_kafka_broker,
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
