"""Retrying outbox worker with DLQ fallback.

This module provides the `ScheduledOutboxWorker` which runs in the background,
polling the outbox repository for unpublished events and publishing them to
Kafka. It handles retries with exponential backoff and routes permanently failed
events to a Dead Letter Queue (DLQ).

See also
--------
- messaging.infrastructure.outbox.outbox_repository : Where events are polled from
- messaging.infrastructure.pubsub.kafka_publisher : Used for publishing
"""

from __future__ import annotations

import asyncio
import logging

from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from messaging.core.contracts import BaseEvent
from messaging.infrastructure.pubsub.dead_letter_handler import DeadLetterHandler
from python_outbox_core import IEventPublisher, IOutboxRepository, OutboxConfig, OutboxPublisherBase

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class ScheduledOutboxWorker(OutboxPublisherBase):
    """Publish outbox events on a polling loop with retry and DLQ support."""

    def __init__(
        self,
        repository: IOutboxRepository,
        publisher: IEventPublisher,
        config: OutboxConfig,
        dead_letter_handler: DeadLetterHandler | None = None,
    ) -> None:
        super().__init__(repository, publisher)
        self._config = config
        self._dead_letter_handler = dead_letter_handler
        self._stop_event = asyncio.Event()

    async def schedule_publishing(self) -> None:
        """Run a polling loop until stop() is called."""
        logger.info("Starting outbox worker polling loop")
        while not self._stop_event.is_set():
            logger.debug("Polling outbox for unpublished events (batch_size=%d)", self._config.batch_size)
            await self.publish_batch(limit=self._config.batch_size)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._config.poll_interval_seconds,
                )
            except TimeoutError:
                continue
        logger.info("Outbox worker polling loop stopped")

    async def stop(self) -> None:
        """Signal the worker loop to exit."""
        self._stop_event.set()

    async def _try_publish(self, event: BaseEvent) -> bool:
        """Publish one event with retries, then route to DLQ on failure."""
        logger.debug("Publishing event %s (type=%s)", event.event_id, event.event_type)
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._config.max_retry_count),
                wait=wait_exponential(multiplier=self._config.retry_backoff_multiplier),
                reraise=True,
            ):
                with attempt:
                    if attempt.retry_state.attempt_number > 1:
                        logger.warning(
                            "Retry %d/%d for event %s",
                            attempt.retry_state.attempt_number,
                            self._config.max_retry_count,
                            event.event_id,
                        )
                    await self.publisher.publish(event.to_message())
            await self.repository.mark_published(event.event_id)
            self.metrics.log_success(event)
            logger.info("Successfully published event %s", event.event_id)
            return True
        except Exception as exc:
            logger.error("Failed to publish event %s after %d retries: %s", event.event_id, self._config.max_retry_count, exc, exc_info=True)
            self.error_handler.handle(event, exc)
            if self._dead_letter_handler is None:
                await self.repository.mark_failed(event.event_id, str(exc))
                logger.warning("Event %s marked as failed (no DLQ handler)", event.event_id)
            else:
                await self._dead_letter_handler.handle(event, str(exc))
                logger.warning("Event %s routed to DLQ", event.event_id)
            return False
