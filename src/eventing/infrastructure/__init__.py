"""Infrastructure layer for the eventing service."""

from eventing.infrastructure.health import EventingHealthCheck
from eventing.infrastructure.messaging import (
    DeadLetterHandler,
    IProcessedMessageStore,
    IdempotentConsumerBase,
    KafkaEventPublisher,
    create_kafka_broker,
)
from eventing.infrastructure.outbox import (
    OutboxEventHandler,
    ScheduledOutboxWorker,
    SqlAlchemyOutboxRepository,
    build_outbox_config,
)
from eventing.infrastructure.persistence import OutboxEventRecord, create_session_factory
from eventing.infrastructure.persistence import (
    ProcessedMessageRecord,
    SqlAlchemyProcessedMessageStore,
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
