"""Unit tests for outbox worker behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest

from messaging.infrastructure.pubsub import DeadLetterHandler
from messaging.infrastructure.outbox import ScheduledOutboxWorker
from python_outbox_core import OutboxConfig
from tests.unit.infrastructure.conftest import ExampleEvent, FakePublisher, FakeRepository


@pytest.mark.asyncio
async def test_worker_marks_events_published_on_success() -> None:
    """Worker should mark events as published when the publisher succeeds."""
    repository = FakeRepository()
    event = ExampleEvent(xp_delta=15, occurred_at=datetime(2026, 3, 30, tzinfo=UTC))
    repository.unpublished = [event]
    worker = ScheduledOutboxWorker(
        repository,
        FakePublisher(),
        OutboxConfig(
            batch_size=100,
            poll_interval_seconds=1,
            max_retry_count=1,
            retry_backoff_multiplier=1.0,
        ),
    )

    published = await worker.publish_batch()

    assert published == 1
    assert repository.published == [event.event_id]


@pytest.mark.asyncio
async def test_worker_routes_failed_events_to_dlq() -> None:
    """Worker should mark and publish failed events to the DLQ."""
    repository = FakeRepository()
    publisher = FakePublisher(should_fail=True)
    dlq_publisher = FakePublisher()
    event = ExampleEvent(xp_delta=25)
    repository.unpublished = [event]
    worker = ScheduledOutboxWorker(
        repository,
        publisher,
        OutboxConfig(
            batch_size=100,
            poll_interval_seconds=1,
            max_retry_count=1,
            retry_backoff_multiplier=1.0,
        ),
        dead_letter_handler=DeadLetterHandler(repository, cast(Any, dlq_publisher)),
    )

    published = await worker.publish_batch()

    assert published == 0
    assert repository.failed == [(event.event_id, "publish failed")]
    assert dlq_publisher.topics == [f"{event.event_type}.DLQ"]
