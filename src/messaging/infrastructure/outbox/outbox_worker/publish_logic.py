"""Publish logic with retries and DLQ fallback.

Handles event publishing with exponential backoff retries and DLQ fallback
for permanently failed events.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from messaging.core.contracts import BaseEvent
    from messaging.infrastructure.pubsub.dead_letter_handler import DeadLetterHandler
    from python_outbox_core import (
        IEventPublisher,
        IOutboxRepository,
        OutboxConfig,
        OutboxErrorHandler,
        OutboxMetrics,
    )

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# pylint: disable=R0913  # too-many-arguments (required for DLQ orchestration)
async def try_publish(
    event: BaseEvent,
    *,
    publisher: IEventPublisher,
    repository: IOutboxRepository,
    config: OutboxConfig,
    dead_letter_handler: DeadLetterHandler | None,
    metrics: OutboxMetrics,
    error_handler: OutboxErrorHandler,
) -> bool:
    """Publish one event with retries, then route to DLQ on failure.

    Args:
        event: The event to publish
        publisher: The publisher instance
        repository: The outbox repository
        config: The outbox configuration
        dead_letter_handler: Optional DLQ handler for failed events
        metrics: OutboxMetrics instance for logging success
        error_handler: OutboxErrorHandler for error handling

    Returns:
        bool: True if published successfully, False if routed to DLQ.
    """
    logger.debug(
        "Publishing event %s (type=%s)", event.event_id, event.event_type,
    )
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(config.max_retry_count),
            wait=wait_exponential(
                multiplier=config.retry_backoff_multiplier,
            ),
            reraise=True,
        ):
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    logger.warning(
                        "Retry %d/%d for event %s",
                        attempt.retry_state.attempt_number,
                        config.max_retry_count,
                        event.event_id,
                    )
                await publisher.publish(event.to_message())
        await repository.mark_published(event.event_id)
        metrics.log_success(event)
        logger.info("Successfully published event %s", event.event_id)
        return True
    except Exception as exc:
        logger.error(
            "Failed to publish event %s after %d retries: %s",
            event.event_id,
            config.max_retry_count,
            exc,
            exc_info=True,
        )
        error_handler.handle(event, exc)
        if dead_letter_handler is None:
            await repository.mark_failed(event.event_id, str(exc))
            logger.warning(
                "Event %s marked as failed (no DLQ handler)", event.event_id,
            )
        else:
            await dead_letter_handler.handle(event, str(exc))
            logger.warning("Event %s routed to DLQ")
        return False
