"""Retrying outbox worker with DLQ fallback."""

from __future__ import annotations

import asyncio

from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from eventing.core.contracts import BaseEvent
from eventing.infrastructure.messaging.dead_letter_handler import DeadLetterHandler
from python_outbox_core import IEventPublisher, IOutboxRepository, OutboxConfig, OutboxPublisherBase


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
        while not self._stop_event.is_set():
            await self.publish_batch(limit=self._config.batch_size)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._config.poll_interval_seconds,
                )
            except TimeoutError:
                continue

    async def stop(self) -> None:
        """Signal the worker loop to exit."""
        self._stop_event.set()

    async def _try_publish(self, event: BaseEvent) -> bool:
        """Publish one event with retries, then route to DLQ on failure."""
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._config.max_retry_count),
                wait=wait_exponential(multiplier=self._config.retry_backoff_multiplier),
                reraise=True,
            ):
                with attempt:
                    await self.publisher.publish(event.to_message())
            await self.repository.mark_published(event.event_id)
            self.metrics.log_success(event)
            return True
        except Exception as exc:
            self.error_handler.handle(event, exc)
            if self._dead_letter_handler is None:
                await self.repository.mark_failed(event.event_id, str(exc))
            else:
                await self._dead_letter_handler.handle(event, str(exc))
            return False
