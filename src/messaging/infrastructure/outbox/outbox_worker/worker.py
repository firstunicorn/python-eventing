"""Retrying outbox worker with DLQ fallback.

This module provides the `ScheduledOutboxWorker` which runs in the background,
polling the outbox repository for unpublished events and publishing them to
Kafka. It handles retries with exponential backoff and routes permanently failed
events to a Dead Letter Queue (DLQ).

See Also
--------
- messaging.infrastructure.outbox.outbox_repository : Where events are polled from
- messaging.infrastructure.pubsub.kafka_publisher : Used for publishing
"""

from __future__ import annotations

import asyncio

from messaging.core.contracts import BaseEvent
from messaging.infrastructure.outbox.outbox_worker.publish_logic import try_publish
from messaging.infrastructure.pubsub.dead_letter_handler import DeadLetterHandler
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
        return await try_publish(
            event=event,
            publisher=self.publisher,
            repository=self.repository,
            config=self._config,
            dead_letter_handler=self._dead_letter_handler,
            metrics=self.metrics,
            error_handler=self.error_handler,
        )
