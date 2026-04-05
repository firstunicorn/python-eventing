"""Integration tests for DLQ routing in the eventing worker."""

from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from messaging.core.contracts import BaseEvent, EventRegistry
from messaging.infrastructure.outbox import ScheduledOutboxWorker
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from messaging.infrastructure.persistence.orm_models.outbox_orm import OutboxEventRecord
from messaging.infrastructure.pubsub import DeadLetterHandler
from python_outbox_core import OutboxConfig
from tests.integration.test_outbox_worker_flow import RecordingPublisher


class ExampleEvent(BaseEvent):  # pylint: disable=too-many-ancestors
    """Concrete integration-test event."""

    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "user-123"
    source: str = "gamification-service"
    xp_delta: int


pytestmark = pytest.mark.asyncio


async def test_worker_routes_failed_records_to_dlq(
    sqlite_session_factory: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    """Failed publications should persist failure state and emit a DLQ payload."""
    _, session_factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(ExampleEvent)
    repository = SqlAlchemyOutboxRepository(session_factory, registry)
    dlq_publisher = RecordingPublisher()
    event = ExampleEvent(xp_delta=40)

    await repository.add_event(event)
    published = await ScheduledOutboxWorker(
        repository,
        RecordingPublisher(should_fail=True),
        OutboxConfig(
            batch_size=100,
            poll_interval_seconds=1,
            max_retry_count=1,
            retry_backoff_multiplier=1.0,
        ),
        dead_letter_handler=DeadLetterHandler(repository, cast(Any, dlq_publisher)),
    ).publish_batch()

    async with session_factory() as session:
        stored = await session.scalar(
            select(OutboxEventRecord).where(OutboxEventRecord.event_id == str(event.event_id))
        )
    assert published == 0
    assert stored is not None
    assert stored.failed is True
    assert dlq_publisher.topics == [f"{event.event_type}.DLQ"]
