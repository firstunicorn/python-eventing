"""Handle method mixin for Kafka dead-letter handler.

Contains the async handle method with full docstrings and execution logic
for routing failed events to Kafka DLQ topics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from messaging.core.contracts import BaseEvent
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler import helpers
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler.execution import (
    execute_dlq,
)
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler.logging import (
    log_dlq_published,
    log_dlq_routing,
)

if TYPE_CHECKING:
    from typing import Protocol

    from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler.config import (
        KafkaDLQConfig,
    )
    from messaging.infrastructure.pubsub.kafka_publisher import KafkaEventPublisher
    from python_outbox_core import IOutboxRepository

    class _HasDLQAttrs(Protocol):
        """Protocol for classes that have DLQ-related attributes."""
        _repository: IOutboxRepository
        _publisher: KafkaEventPublisher
        _config: KafkaDLQConfig


class KafkaDeadLetterHandleMixin:
    """Mixin providing handle method with full DLQ orchestration."""

    if TYPE_CHECKING:
        _repository: IOutboxRepository
        _publisher: KafkaEventPublisher
        _config: KafkaDLQConfig

    async def handle(
        self,
        event: BaseEvent,
        error_message: str,
        *,
        retry_count: int = 0,
        original_topic: str | None = None,
    ) -> None:
        """Persist failure details and publish to Kafka DLQ with rich metadata.

        This method adds Kafka-specific enhancements:
        - Custom headers for error tracking and debugging
        - Partition key preservation for ordered processing
        - Timestamp preservation for accurate event timeline

        Parameters
        ----------
        event : BaseEvent
            The domain event that failed to publish
        error_message : str
            Description of the failure reason
        retry_count : int, optional
            Number of retry attempts before DLQ routing (default: 0)
        original_topic : str | None, optional
            The original topic where the event should have been published
        """
        log_dlq_routing(event, error_message, retry_count)

        await execute_dlq(
            repository=self._repository,
            publisher=self._publisher,
            helpers=helpers,
            event=event,
            error_message=error_message,
            retry_count=retry_count,
            original_topic=original_topic,
            include_headers=self._config.include_headers,
        )

        log_dlq_published(event.event_id, f"{event.event_type}.DLQ", self._config.include_headers)
