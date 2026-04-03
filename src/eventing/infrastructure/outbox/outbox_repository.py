"""SQLAlchemy implementation of the outbox repository contract.

This module provides `SqlAlchemyOutboxRepository` which implements the CRUD
operations for storing domain events in the database transactionally alongside
business data. It also tracks the published/failed status of events.

See also
--------
- eventing.infrastructure.persistence.outbox_orm : The underlying ORM model
- eventing.infrastructure.outbox.outbox_worker : The worker that reads these events
"""

# pylint: disable=too-many-lines

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from eventing.core.contracts import BaseEvent, EventRegistry
from eventing.infrastructure.persistence.outbox_orm import OutboxEventRecord
from python_outbox_core import IOutboxEvent, IOutboxRepository


class SqlAlchemyOutboxRepository(IOutboxRepository):
    """Persist and retrieve outbox events with SQLAlchemy async sessions."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: EventRegistry,
    ) -> None:
        self._session_factory = session_factory
        self._registry = registry

    async def add_event(self, event: IOutboxEvent) -> None:
        """Store a serialized event without committing the transaction."""
        async with self._session_factory() as session:
            session.add(self._to_record(event))
            await session.commit()

    async def get_unpublished(self, limit: int = 100, offset: int = 0) -> list[IOutboxEvent]:
        """Fetch unpublished events ordered by creation time."""
        statement = (
            select(OutboxEventRecord)
            .where(OutboxEventRecord.published.is_(False), OutboxEventRecord.failed.is_(False))
            .order_by(OutboxEventRecord.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        async with self._session_factory() as session:
            records = (await session.scalars(statement)).all()
        return [self._registry.deserialize(record.payload) for record in records]

    async def mark_published(self, event_id: UUID) -> None:
        """Mark an event as published and timestamp the update."""
        await self._mark(str(event_id), published=True, published_at=datetime.now(UTC))

    async def count_unpublished(self) -> int:
        """Count pending unpublished and non-failed events."""
        statement = select(func.count()).select_from(OutboxEventRecord).where(
            OutboxEventRecord.published.is_(False),
            OutboxEventRecord.failed.is_(False),
        )
        async with self._session_factory() as session:
            return int(await session.scalar(statement) or 0)

    async def mark_failed(self, event_id: UUID, error_message: str) -> None:
        """Persist failure state and error details for an event."""
        await self._mark(
            str(event_id),
            failed=True,
            failed_at=datetime.now(UTC),
            error_message=error_message,
        )

    async def ping(self) -> bool:
        """Check if the backing database is reachable."""
        async with self._session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True

    async def oldest_unpublished_age_seconds(self) -> float:
        """Return the age of the oldest pending event in seconds."""
        statement = select(func.min(OutboxEventRecord.created_at)).where(
            OutboxEventRecord.published.is_(False),
            OutboxEventRecord.failed.is_(False),
        )
        async with self._session_factory() as session:
            oldest = await session.scalar(statement)
        if oldest is None:
            return 0.0
        return max((datetime.now(UTC) - oldest.astimezone(UTC)).total_seconds(), 0.0)

    async def _mark(self, event_id: str, **values: object) -> None:
        statement = (
            update(OutboxEventRecord)
            .where(OutboxEventRecord.event_id == event_id)
            .values(**values)
        )
        async with self._session_factory() as session:
            await session.execute(statement)
            await session.commit()

    @staticmethod
    def _to_record(event: IOutboxEvent) -> OutboxEventRecord:
        payload = event.to_message()
        base_event = BaseEvent.model_validate(payload)
        return OutboxEventRecord(
            event_id=str(event.event_id),
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            payload=payload,
            occurred_at=base_event.occurred_at,
        )
