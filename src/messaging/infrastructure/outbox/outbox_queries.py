"""Query operations for outbox event status and metrics.

This module provides `OutboxQueryOperations` which handles read-only
queries for outbox status, including unpublished event retrieval,
counts, and lag metrics.

See also
--------
- messaging.infrastructure.outbox.outbox_crud : Create and update operations
- messaging.infrastructure.outbox.outbox_repository : The facade repository
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from messaging.core.contracts import EventRegistry
from messaging.infrastructure.persistence.orm_models.outbox_orm import OutboxEventRecord
from python_outbox_core import IOutboxEvent

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class OutboxQueryOperations:
    """Handle read-only queries for outbox status."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], registry: EventRegistry
    ) -> None:
        self._session_factory = session_factory
        self._registry = registry

    async def get_unpublished(self, limit: int = 100, offset: int = 0) -> list[IOutboxEvent]:
        """Fetch unpublished events ordered by creation time."""
        logger.debug("Fetching unpublished events (limit=%d, offset=%d)", limit, offset)
        statement = (
            select(OutboxEventRecord)
            .where(OutboxEventRecord.published.is_(False), OutboxEventRecord.failed.is_(False))
            .order_by(OutboxEventRecord.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        async with self._session_factory() as session:
            records = (await session.scalars(statement)).all()
        logger.debug("Retrieved %d unpublished events", len(records))
        return [self._registry.deserialize(record.payload) for record in records]

    async def count_unpublished(self) -> int:
        """Count pending unpublished and non-failed events."""
        statement = select(func.count()).select_from(OutboxEventRecord).where(
            OutboxEventRecord.published.is_(False),
            OutboxEventRecord.failed.is_(False),
        )
        async with self._session_factory() as session:
            return int(await session.scalar(statement) or 0)

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

    async def ping(self) -> bool:
        """Check if the backing database is reachable."""
        async with self._session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
