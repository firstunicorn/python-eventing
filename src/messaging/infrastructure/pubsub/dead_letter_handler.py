"""Dead-letter routing for permanently failed events.

This module provides the `DeadLetterHandler` which is used by the outbox worker
when an event fails to publish after all retry attempts are exhausted. It marks
the event as failed in the database and publishes it to a designated DLQ topic.

See also
--------
- messaging.infrastructure.outbox.outbox_worker : The worker that triggers this handler
"""

import logging

from messaging.core.contracts import BaseEvent
from messaging.infrastructure.pubsub.kafka_publisher import KafkaEventPublisher
from python_outbox_core import IOutboxRepository

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class DeadLetterHandler:
    """Mark failed outbox records and publish them to a DLQ topic."""

    def __init__(self, repository: IOutboxRepository, publisher: KafkaEventPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    async def handle(self, event: BaseEvent, error_message: str) -> None:
        """Persist failure details and publish the event to its DLQ topic."""
        logger.warning(
            "Routing event %s (type=%s) to DLQ: %s",
            event.event_id,
            event.event_type,
            error_message,
        )
        await self._repository.mark_failed(event.event_id, error_message)
        message = {"event": event.to_message(), "error": error_message}
        dlq_topic = f"{event.event_type}.DLQ"
        await self._publisher.publish_to_topic(dlq_topic, message)
        logger.info("Event %s published to DLQ topic '%s'", event.event_id, dlq_topic)
