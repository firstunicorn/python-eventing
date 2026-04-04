"""Kafka messaging adapters and consumer patterns.

This module provides Kafka integration with built-in reliability patterns:

**Publishing**
  - KafkaEventPublisher : Publish CloudEvents to Kafka topics
  - Resolves topic from event metadata
  - Handles serialization and error recovery

**Consuming**
  - IdempotentConsumerBase : Base class for replay-safe consumers
  - Automatic deduplication using ProcessedMessageStore
  - Prevents duplicate processing on Kafka redelivery

**Dead Letter Queue**
  - DeadLetterHandler : Route failures to DLQ topics
  - Preserves original event metadata for debugging
  - KafkaDeadLetterHandler : Kafka-specific DLQ with headers

**Configuration**
  - create_kafka_broker : FastStream Kafka broker factory
  - IProcessedMessageStore : Interface for idempotency stores

See also
--------
- messaging.infrastructure.persistence : Idempotency store implementations
- messaging.infrastructure.outbox : Outbox worker uses KafkaEventPublisher
"""

from messaging.infrastructure.pubsub.broker_config import create_kafka_broker
from messaging.infrastructure.pubsub.dead_letter_handler import DeadLetterHandler
from messaging.infrastructure.pubsub.consumer_base.kafka_consumer_base import IdempotentConsumerBase
from messaging.infrastructure.pubsub.kafka_publisher import KafkaEventPublisher
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler import (
    KafkaDeadLetterHandler,
    build_dlq_message,
    build_kafka_headers,
    KafkaDLQConfig,
    log_dlq_published,
    log_dlq_routing,
)
from messaging.infrastructure.pubsub.processed_message_store import IProcessedMessageStore

__all__ = [
    "DeadLetterHandler",
    "IProcessedMessageStore",
    "IdempotentConsumerBase",
    "KafkaDLQConfig",
    "KafkaDeadLetterHandler",
    "KafkaEventPublisher",
    "build_dlq_message",
    "build_kafka_headers",
    "create_kafka_broker",
    "log_dlq_published",
    "log_dlq_routing",
]
