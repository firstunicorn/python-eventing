"""Kafka-specific messaging components.

This package provides Kafka-specific implementations that extend the
universal messaging infrastructure with Kafka features like headers,
partition keys, and advanced topic configuration.

See also
--------
- messaging.infrastructure.messaging : Universal messaging components
"""

from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler import (
    KafkaDeadLetterHandler,
)

__all__ = ["KafkaDeadLetterHandler"]
