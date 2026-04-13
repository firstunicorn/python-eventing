"""Status marking operations for outbox events."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from messaging.infrastructure.persistence.orm_models.outbox_orm import OutboxEventRecord

logger = logging.getLogger(__name__)


async def mark_published(
    event_id: UUID,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Mark an event as published and timestamp the update."""
    logger.debug("Marking event %s as published", event_id)
    await _mark_status(
        str(event_id),
        session_factory,
        published=True,
        published_at=datetime.now(UTC),
    )


async def mark_failed(
    event_id: UUID,
    error_message: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Persist failure state and error details for an event."""
    logger.warning("Marking event %s as failed: %s", event_id, error_message)
    await _mark_status(
        str(event_id),
        session_factory,
        failed=True,
        failed_at=datetime.now(UTC),
        error_message=error_message,
    )


async def reset_failed(
    event_id: UUID,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Reset failed event for retry.

    Clear failed status, error, and increment attempt counter.

    Args:
        event_id: UUID of the failed event to reset
        session_factory: SQLAlchemy async session factory
    """
    logger.info("Resetting failed status for event %s (incrementing attempt counter)", event_id)

    async with session_factory() as session:
        result = await session.execute(
            select(OutboxEventRecord.attempt_count).where(
                OutboxEventRecord.event_id == str(event_id)
            )
        )
        current_attempts = result.scalar_one_or_none() or 0

    await _mark_status(
        str(event_id),
        session_factory,
        published=False,
        failed=False,
        failed_at=None,
        error_message=None,
        attempt_count=current_attempts + 1,
    )


async def _mark_status(
    event_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    **values: object,
) -> None:
    """Generic update helper for status changes."""
    statement = (
        update(OutboxEventRecord)
        .where(OutboxEventRecord.event_id == event_id)
        .values(**values)
    )
    async with session_factory() as session:
        await session.execute(statement)
        await session.commit()
