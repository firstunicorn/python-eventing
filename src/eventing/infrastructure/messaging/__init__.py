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

**Configuration**
  - create_kafka_broker : FastStream Kafka broker factory
  - IProcessedMessageStore : Interface for idempotency stores

See also
--------
- eventing.infrastructure.persistence : Idempotency store implementations
- eventing.infrastructure.outbox : Outbox worker uses KafkaEventPublisher
"""

from eventing.infrastructure.messaging.broker_config import create_kafka_broker
from eventing.infrastructure.messaging.dead_letter_handler import DeadLetterHandler
from eventing.infrastructure.messaging.kafka_consumer_base import IdempotentConsumerBase
from eventing.infrastructure.messaging.kafka_publisher import KafkaEventPublisher
from eventing.infrastructure.messaging.processed_message_store import IProcessedMessageStore

__all__ = [
    "DeadLetterHandler",
    "IProcessedMessageStore",
    "IdempotentConsumerBase",
    "KafkaEventPublisher",
    "create_kafka_broker",
]
