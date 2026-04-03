"""Integration tests for the eventing outbox repository."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from eventing.core.contracts import BaseEvent, EventRegistry
from eventing.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from eventing.infrastructure.persistence.outbox_orm import OutboxEventRecord


class ExampleEvent(BaseEvent):  # pylint: disable=too-many-ancestors
    """Concrete integration-test event."""

    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "user-123"
    source: str = "gamification-service"
    xp_delta: int


pytestmark = pytest.mark.asyncio


async def test_repository_round_trips_unpublished_events(
    sqlite_session_factory: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    """Persisted outbox events should round-trip through the real database."""
    _, session_factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(ExampleEvent)
    repository = SqlAlchemyOutboxRepository(session_factory, registry)
    event = ExampleEvent(xp_delta=20, occurred_at=datetime(2026, 3, 31, tzinfo=UTC))

    await repository.add_event(event)

    unpublished = await repository.get_unpublished()
    assert len(unpublished) == 1
    assert unpublished[0].to_message() == event.to_message()
    assert await repository.count_unpublished() == 1


async def test_repository_marks_events_published(
    sqlite_session_factory: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    """Marking an outbox event as published should update the stored record."""
    _, session_factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(ExampleEvent)
    repository = SqlAlchemyOutboxRepository(session_factory, registry)
    event = ExampleEvent(xp_delta=30)

    await repository.add_event(event)
    await repository.mark_published(event.event_id)

    async with session_factory() as session:
        stored = await session.scalar(
            select(OutboxEventRecord).where(OutboxEventRecord.event_id == str(event.event_id))
        )
    assert stored is not None
    assert stored.published is True
    assert stored.published_at is not None
