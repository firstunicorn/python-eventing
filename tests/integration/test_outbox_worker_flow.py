"""Integration tests for the eventing outbox worker and health check."""

from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from eventing.core.contracts import BaseEvent, EventRegistry
from eventing.infrastructure.health import EventingHealthCheck
from eventing.infrastructure.outbox import ScheduledOutboxWorker
from eventing.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from python_outbox_core import OutboxConfig


class ExampleEvent(BaseEvent):  # pylint: disable=too-many-ancestors
    """Concrete integration-test event."""

    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "user-123"
    source: str = "gamification-service"
    xp_delta: int


class RecordingPublisher:
    """Publisher fake that records successful and DLQ publications."""

    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail
        self.messages: list[dict[str, object]] = []
        self.topics: list[str] = []

    async def publish(self, message: dict[str, object]) -> None:
        """Store one published payload or fail deterministically."""
        if self._should_fail:
            msg = "publish failed"
            raise RuntimeError(msg)
        self.messages.append(message)

    async def publish_to_topic(self, topic: str, message: dict[str, object]) -> None:
        """Store one DLQ publication."""
        self.topics.append(topic)
        self.messages.append(message)


class HealthyBroker:
    """Broker fake that always reports healthy."""

    async def ping(self, timeout: float | None) -> bool:
        """Return a successful broker ping response."""
        return timeout == 1.0


pytestmark = pytest.mark.asyncio


async def test_worker_publishes_real_records_and_health_sees_backlog(
    sqlite_session_factory: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    """The worker should publish stored records and health should inspect the same database."""
    _, session_factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(ExampleEvent)
    repository = SqlAlchemyOutboxRepository(session_factory, registry)
    publisher = RecordingPublisher()
    event = ExampleEvent(xp_delta=25)

    await repository.add_event(event)
    before = await EventingHealthCheck(
        cast(Any, repository),
        cast(Any, HealthyBroker()),
        lag_threshold=0,
    ).check_health()
    published = await ScheduledOutboxWorker(
        repository,
        publisher,
        OutboxConfig(
            batch_size=100,
            poll_interval_seconds=1,
            max_retry_count=1,
            retry_backoff_multiplier=1.0,
        ),
    ).publish_batch()

    assert before["status"] == "degraded"
    assert before["checks"]["outbox"]["pending_count"] == 1
    assert published == 1
    assert publisher.messages[0]["eventType"] == event.event_type
