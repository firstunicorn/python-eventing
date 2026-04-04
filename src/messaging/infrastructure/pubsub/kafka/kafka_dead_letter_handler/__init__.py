"""Kafka dead-letter handler module."""

from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler.config import (
    KafkaDLQConfig,
)
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler.execution import (
    execute_dlq,
)
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler.handler import (
    KafkaDeadLetterHandler,
)
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler.helpers import (
    build_dlq_message,
    build_kafka_headers,
)
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler.logging import (
    log_dlq_published,
    log_dlq_routing,
)

__all__ = [
    "KafkaDLQConfig",
    "KafkaDeadLetterHandler",
    "build_dlq_message",
    "build_kafka_headers",
    "execute_dlq",
    "log_dlq_published",
    "log_dlq_routing",
]
