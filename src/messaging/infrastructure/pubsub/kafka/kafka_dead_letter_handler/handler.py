"""Core KafkaDeadLetterHandler class.

Wraps IOutboxRepository and KafkaEventPublisher into a handler with
Kafka-specific features (headers, partition key preservation). Uses
KafkaDLQConfig for options and delegates execution to helpers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler.config import KafkaDLQConfig
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler.handler_mixin import (
    KafkaDeadLetterHandleMixin,
)
from messaging.infrastructure.pubsub.kafka_publisher import KafkaEventPublisher
from python_outbox_core import IOutboxRepository

if TYPE_CHECKING:
    pass


class KafkaDeadLetterHandler(KafkaDeadLetterHandleMixin):
    """Mark failed outbox records and publish them to Kafka DLQ with advanced features.

    This handler leverages Kafka-specific capabilities:
    - Custom headers (error metadata, retry count, original topic)
    - Partition key preservation (maintains event ordering)
    - Timestamp control (preserves original event time)
    - Kafka-specific topic configuration

    If you don't need these Kafka features, use the universal DeadLetterHandler
    which works with any message broker.
    """

    _repository: IOutboxRepository
    _publisher: KafkaEventPublisher
    _config: KafkaDLQConfig

    def __init__(
        self,
        repository: IOutboxRepository,
        publisher: KafkaEventPublisher,
        *,
        include_headers: bool = True,
        preserve_partition_key: bool = True,
    ) -> None:
        """Initialize the Kafka-specific DLQ handler.

        Args:
            self: The class instance
            repository (IOutboxRepository): Repository for marking events as failed
            publisher (KafkaEventPublisher): Kafka event publisher (concrete type for
                Kafka features)
            include_headers (bool, optional): Whether to add Kafka headers with error
                metadata (default: True)
            preserve_partition_key (bool, optional): Whether to use the same partition
                key as the original event (default: True)
        """
        self._repository = repository
        self._publisher = publisher
        self._config = KafkaDLQConfig(
            include_headers=include_headers,
            preserve_partition_key=preserve_partition_key,
        )
