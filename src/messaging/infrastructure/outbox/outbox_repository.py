"""SQLAlchemy implementation of the outbox repository contract.

This module provides `SqlAlchemyOutboxRepository` which implements the CRUD
operations for storing domain events in the database transactionally alongside
business data. It delegates to specialized CRUD and query operation classes.

See also
--------
- messaging.infrastructure.outbox.outbox_crud : Create and update operations
- messaging.infrastructure.outbox.outbox_queries : Query and metrics operations
- messaging.infrastructure.persistence.outbox_orm : The underlying ORM model
- messaging.infrastructure.outbox.outbox_worker : The worker that reads these events
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from messaging.core.contracts import EventRegistry
from messaging.infrastructure.outbox.outbox_crud import OutboxCrudOperations
from messaging.infrastructure.outbox.outbox_queries import OutboxQueryOperations
from python_outbox_core import IOutboxEvent, IOutboxRepository


class SqlAlchemyOutboxRepository(IOutboxRepository):
    """Persist and retrieve outbox events with SQLAlchemy async sessions.

    This facade delegates to specialized CRUD and query operations,
    maintaining the IOutboxRepository interface while keeping each
    concern in a separate focused class.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: EventRegistry,
    ) -> None:
        self._crud = OutboxCrudOperations(session_factory)
        self._queries = OutboxQueryOperations(session_factory, registry)

    async def add_event(self, event: IOutboxEvent, session: AsyncSession | None = None) -> None:
        """Store a serialized event in the provided or new session."""
        await self._crud.add_event(event, session)

    async def get_unpublished(self, limit: int = 100, offset: int = 0) -> list[IOutboxEvent]:
        """Fetch unpublished events ordered by creation time."""
        return await self._queries.get_unpublished(limit, offset)

    async def mark_published(self, event_id: UUID) -> None:
        """Mark an event as published and timestamp the update."""
        await self._crud.mark_published(event_id)

    async def count_unpublished(self) -> int:
        """Count pending unpublished and non-failed events."""
        return await self._queries.count_unpublished()

    async def mark_failed(self, event_id: UUID, error_message: str) -> None:
        """Persist failure state and error details for an event."""
        await self._crud.mark_failed(event_id, error_message)

    async def ping(self) -> bool:
        """Check if the backing database is reachable."""
        return await self._queries.ping()

    async def oldest_unpublished_age_seconds(self) -> float:
        """Return the age of the oldest pending event in seconds."""
        return await self._queries.oldest_unpublished_age_seconds()

