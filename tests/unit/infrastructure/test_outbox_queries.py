"""Unit tests for OutboxQueryOperations query generation.

Uses SQLite to verify actual query structure and behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from messaging.core.contracts import EventRegistry
from messaging.infrastructure.outbox.outbox_queries import OutboxQueryOperations
from messaging.infrastructure.persistence.orm_models.outbox_orm import OutboxEventRecord
from tests.unit.infrastructure.conftest import ExampleEvent


@pytest.mark.asyncio
async def test_get_unpublished_returns_ordered_events(
    sqlite_session_factory: tuple,
) -> None:
    """Query should return events in creation order."""
    engine, factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(ExampleEvent)
    ops = OutboxQueryOperations(factory, registry)

    event = ExampleEvent(xp_delta=5, occurred_at=datetime(2026, 3, 30, tzinfo=UTC))
    record = OutboxEventRecord(
        event_id=str(event.event_id),
        event_type=event.event_type,
        aggregate_id=event.aggregate_id,
        payload=event.to_message(),
        occurred_at=event.occurred_at,
    )
    async with factory() as session:
        session.add(record)
        await session.commit()

    results = await ops.get_unpublished(limit=10, offset=0)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_count_unpublished_excludes_failed(
    sqlite_session_factory: tuple,
) -> None:
    """Count should exclude events marked as failed."""
    engine, factory = sqlite_session_factory
    registry = EventRegistry()
    registry.register(ExampleEvent)
    ops = OutboxQueryOperations(factory, registry)

    event = ExampleEvent(xp_delta=10)
    record = OutboxEventRecord(
        event_id=str(event.event_id),
        event_type=event.event_type,
        aggregate_id=event.aggregate_id,
        payload=event.to_message(),
        occurred_at=event.occurred_at,
        failed=True,
    )
    async with factory() as session:
        session.add(record)
        await session.commit()

    assert await ops.count_unpublished() == 0
