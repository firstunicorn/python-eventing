"""Test for outbox metrics accuracy after mixed success/failure runs."""

from __future__ import annotations

import pytest

from messaging.core.contracts import BaseEvent, EventRegistry
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from messaging.infrastructure.outbox.outbox_worker.worker import ScheduledOutboxWorker
from python_outbox_core import OutboxConfig


class MetricsEvent(BaseEvent):
    event_type: str = "metrics.test"
    aggregate_id: str = "metrics-001"
    source: str = "metrics-test"
    xp_delta: int = 0


class CountingPublisher:
    def __init__(self, fail_indices: set[int]) -> None:
        self._fail_indices = fail_indices
        self._call_count = 0
        self.success_count = 0
        self.failure_count = 0

    async def publish(self, message: dict[str, object]) -> None:
        self._call_count += 1
        if self._call_count in self._fail_indices:
            self.failure_count += 1
            msg = "publish failed"
            raise RuntimeError(msg)
        self.success_count += 1

    async def publish_to_topic(
        self,
        topic: str,
        message: dict[str, object],
    ) -> None:
        self._call_count += 1
        if self._call_count in self._fail_indices:
            self.failure_count += 1
            msg = "publish failed"
            raise RuntimeError(msg)
        self.success_count += 1


@pytest.mark.asyncio
async def test_metrics_accuracy_mixed_results(
    sqlite_session_factory: tuple,
) -> None:
    success_count = 3
    failure_count = 2
    total = success_count + failure_count
    _, factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(MetricsEvent)
    repo = SqlAlchemyOutboxRepository(factory, registry)
    for i in range(total):
        await repo.add_event(MetricsEvent(xp_delta=i))
    publisher = CountingPublisher(fail_indices={1, 3})
    worker = ScheduledOutboxWorker(
        repo,
        publisher,
        OutboxConfig(
            batch_size=total,
            poll_interval_seconds=1,
            max_retry_count=0,
            retry_backoff_multiplier=1.0,
        ),
    )
    result = await worker.publish_batch()
    assert result == publisher.success_count
    assert publisher.success_count == success_count
    assert publisher.failure_count == failure_count
    unpublished = await repo.get_unpublished()
    assert len(unpublished) == total - success_count
