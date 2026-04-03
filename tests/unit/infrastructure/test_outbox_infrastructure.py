"""Unit tests for outbox infrastructure behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from eventing.core.events import BaseEvent
from eventing.infrastructure.health import EventingHealthCheck
from eventing.infrastructure.messaging import (
    DeadLetterHandler,
    KafkaEventPublisher,
)
from eventing.infrastructure.outbox import OutboxEventHandler, ScheduledOutboxWorker
from python_outbox_core import IOutboxEvent, OutboxConfig


class ExampleEvent(BaseEvent):  # pylint: disable=too-many-ancestors
    """Concrete test event for infrastructure behavior."""

    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "user-123"
    source: str = "gamification-service"
    xp_delta: int


class FakeRepository:
    """Minimal async repository fake for worker and health tests."""

    def __init__(self) -> None:
        self.added: list[IOutboxEvent] = []
        self.unpublished: list[IOutboxEvent] = []
        self.published: list[UUID] = []
        self.failed: list[tuple[UUID, str]] = []
        self.pending_count = 0
        self.oldest_age = 0.0
        self.pinged = False

    async def add_event(self, event: IOutboxEvent) -> None:
        self.added.append(event)

    async def get_unpublished(self, limit: int = 100, offset: int = 0) -> list[IOutboxEvent]:
        return self.unpublished[offset : offset + limit]

    async def mark_published(self, event_id: UUID) -> None:
        self.published.append(event_id)

    async def count_unpublished(self) -> int:
        return self.pending_count

    async def mark_failed(self, event_id: UUID, error_message: str) -> None:
        self.failed.append((event_id, error_message))

    async def ping(self) -> bool:
        self.pinged = True
        return True

    async def oldest_unpublished_age_seconds(self) -> float:
        return self.oldest_age


class FakePublisher:
    """Publisher fake with configurable failure mode."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.messages: list[dict[str, object]] = []
        self.topics: list[str] = []

    async def publish(self, message: dict[str, object]) -> None:
        if self.should_fail:
            msg = "publish failed"
            raise RuntimeError(msg)
        self.messages.append(message)

    async def publish_to_topic(self, topic: str, message: dict[str, object]) -> None:
        self.topics.append(topic)
        self.messages.append(message)


class FakeBroker:
    """Broker fake for health check testing."""

    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy

    async def ping(self, timeout: float | None) -> bool:
        return self.healthy and timeout == 1.0


@pytest.mark.asyncio
async def test_outbox_event_handler_persists_event() -> None:
    """Outbox handler should store dispatched events."""
    repository = FakeRepository()
    handler = OutboxEventHandler(repository)
    event = ExampleEvent(xp_delta=10)

    await handler.handle(event)

    assert repository.added == [event]


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


@pytest.mark.asyncio
async def test_health_check_reports_lag_degradation() -> None:
    """Health check should degrade when the outbox backlog is stale."""
    repository = FakeRepository()
    repository.pending_count = 5
    repository.oldest_age = 600.0
    health_check = EventingHealthCheck(
        cast(Any, repository),
        cast(Any, FakeBroker()),
        lag_threshold=2,
    )

    result = await health_check.check_health()

    assert result["checks"]["database"]["status"] == "healthy"
    assert result["checks"]["outbox"]["status"] == "degraded"
    assert result["status"] == "degraded"


def test_kafka_publisher_uses_event_type_as_topic() -> None:
    """Publisher should derive Kafka topic names from event type."""
    publisher = KafkaEventPublisher(cast(Any, FakePublisher()))
    topic = publisher._resolve_topic({"eventType": "gamification.XPAwarded"})

    assert topic == "gamification.XPAwarded"
