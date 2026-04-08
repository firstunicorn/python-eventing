"""Core CRUD operations for outbox events.

This module provides `OutboxCrudOperations` which handles create and update
operations for outbox events. It supports both standalone mode (auto-commit)
and transactional mode (external session) for the outbox pattern.

See Also
--------
- messaging.infrastructure.outbox.outbox_queries : Query operations
- messaging.infrastructure.outbox.outbox_repository : The facade repository
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from messaging.core.contracts import BaseEvent
from messaging.infrastructure.persistence.orm_models.outbox_orm import OutboxEventRecord
from python_outbox_core import IOutboxEvent

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class OutboxCrudOperations:
    """Handle basic create and update operations for outbox events."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add_event(self, event: IOutboxEvent, session: AsyncSession | None = None) -> None:
        """Store a serialized event in the provided or new session.

        For transactional outbox: pass an external session to commit atomically
        with business data. For standalone use: omit session to auto-commit.

        Args:
            event (IOutboxEvent): The serialized event to store
            session (AsyncSession | None): External session for transactional
                outbox, or None to auto-commit in a new session
        """
        logger.debug("Adding event %s (type=%s) to outbox", event.event_id, event.event_type)

        if session is not None:
            session.add(self._to_record(event))
            logger.debug(
                "Event %s added to external session (caller controls commit)",
                event.event_id,
            )
        else:
            async with self._session_factory() as new_session:
                new_session.add(self._to_record(event))
                await new_session.commit()
            logger.debug("Event %s added to outbox and committed", event.event_id)

    async def mark_published(self, event_id: UUID) -> None:
        """Mark an event as published and timestamp the update."""
        logger.debug("Marking event %s as published", event_id)
        await self._mark(str(event_id), published=True, published_at=datetime.now(UTC))

    async def mark_failed(self, event_id: UUID, error_message: str) -> None:
        """Persist failure state and error details for an event."""
        logger.warning("Marking event %s as failed: %s", event_id, error_message)
        await self._mark(
            str(event_id),
            failed=True,
            failed_at=datetime.now(UTC),
            error_message=error_message,
        )

    async def reset_failed(self, event_id: UUID) -> None:
        """Reset failed event for retry: clear failed status, error, and increment attempt counter.
        
        Args:
            event_id: UUID of the failed event to reset
        """
        logger.info("Resetting failed status for event %s (incrementing attempt counter)", event_id)

        # Get current attempt count
        from sqlalchemy import select
        async with self._session_factory() as session:
            result = await session.execute(
                select(OutboxEventRecord.attempt_count).where(
                    OutboxEventRecord.event_id == str(event_id)
                )
            )
            current_attempts = result.scalar_one_or_none() or 0

        # Reset with incremented counter
        await self._mark(
            str(event_id),
            published=False,
            failed=False,
            failed_at=None,
            error_message=None,
            attempt_count=current_attempts + 1,
        )

    async def _mark(self, event_id: str, **values: object) -> None:
        """Generic update helper for status changes."""
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
        """Convert domain event to ORM record."""
        payload = event.to_message()
        base_event = BaseEvent.model_validate(payload)
        return OutboxEventRecord(
            event_id=str(event.event_id),
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            payload=payload,
            occurred_at=base_event.occurred_at,
        )
