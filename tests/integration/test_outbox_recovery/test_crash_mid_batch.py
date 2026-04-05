"""Integration tests for outbox worker crash recovery and batch limits."""

from __future__ import annotations

import pytest

from messaging.core.contracts import BaseEvent, EventRegistry
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from messaging.infrastructure.outbox.outbox_worker.worker import ScheduledOutboxWorker
from python_outbox_core import OutboxConfig


class RecoveryEvent(BaseEvent):
    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "recovery-001"
    source: str = "recovery-test"
    xp_delta: int = 0


class FlakyPublisher:
    def __init__(self, fail_n_times: int = 0) -> None:
        self._fail_n = fail_n_times
        self._fail_count = 0
        self.messages: list[dict[str, object]] = []

    async def publish(self, message: dict[str, object]) -> None:
        if self._fail_count < self._fail_n:
            self._fail_count += 1
            msg = "publish failed"
            raise RuntimeError(msg)
        self.messages.append(message)

    async def publish_to_topic(
        self, topic: str, message: dict[str, object],
    ) -> None:
        self.messages.append(message)


@pytest.mark.asyncio
async def test_publish_succeeds_after_recovery(
    sqlite_session_factory: tuple,
) -> None:
    """Events that fail should be retried and eventually published."""
    _, factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(RecoveryEvent)
    repository = SqlAlchemyOutboxRepository(factory, registry)
    event = RecoveryEvent(xp_delta=1)
    await repository.add_event(event)
    publisher = FlakyPublisher(fail_n_times=2)
    worker = ScheduledOutboxWorker(
        repository, publisher, OutboxConfig(
            batch_size=10, poll_interval_seconds=1,
            max_retry_count=3, retry_backoff_multiplier=1.0),
    )
    published = await worker.publish_batch()
    assert published == 1
    assert len(publisher.messages) == 1


@pytest.mark.asyncio
async def test_batch_size_enforcement(
    sqlite_session_factory: tuple,
) -> None:
    """Worker should publish at most limit events per call."""
    _, factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(RecoveryEvent)
    repository = SqlAlchemyOutboxRepository(factory, registry)
    for i in range(50):
        await repository.add_event(RecoveryEvent(xp_delta=i))
    publisher = FlakyPublisher()
    worker = ScheduledOutboxWorker(
        repository, publisher, OutboxConfig(
            batch_size=5, poll_interval_seconds=1,
            max_retry_count=1, retry_backoff_multiplier=1.0),
    )
    published = await worker.publish_batch(limit=5)
    assert published == 5
    assert len(publisher.messages) == 5
    remaining = await repository.get_unpublished()
    assert len(remaining) == 45
