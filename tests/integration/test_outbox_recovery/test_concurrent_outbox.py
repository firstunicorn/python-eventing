"""Tests for concurrent outbox double-publish behavior."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from messaging.core.contracts import BaseEvent, EventRegistry
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from messaging.infrastructure.outbox.outbox_worker.worker import ScheduledOutboxWorker
from python_outbox_core import OutboxConfig


class IdemEvent(BaseEvent):
    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "idem-001"
    source: str = "concurrent-test"
    xp_delta: int = 42


class RecordingPublisher:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []
        self.lock = asyncio.Lock()

    async def publish(self, message: dict[str, object]) -> None:
        async with self.lock:
            await asyncio.sleep(0.05)
            self.messages.append(message)

    async def publish_to_topic(
        self, topic: str, message: dict[str, object],
    ) -> None:
        async with self.lock:
            self.messages.append(message)


@pytest.mark.asyncio
async def test_concurrent_publish_no_double_publish(
    sqlite_session_factory: tuple,
) -> None:
    """Sequential worker calls should not double-publish."""
    _, factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(IdemEvent)
    repository = SqlAlchemyOutboxRepository(factory, registry)
    event = IdemEvent(occurred_at=datetime.now(tz=UTC))
    await repository.add_event(event)
    publisher = RecordingPublisher()
    w1 = ScheduledOutboxWorker(
        repository, publisher, OutboxConfig(
            batch_size=10, poll_interval_seconds=1,
            max_retry_count=0, retry_backoff_multiplier=1.0),
    )
    r1 = await w1.publish_batch()
    assert r1 == 1
    assert len(publisher.messages) == 1
    w2 = ScheduledOutboxWorker(
        repository, publisher, OutboxConfig(
            batch_size=10, poll_interval_seconds=1,
            max_retry_count=0, retry_backoff_multiplier=1.0),
    )
    r2 = await w2.publish_batch()
    assert r2 == 0
    assert len(publisher.messages) == 1
