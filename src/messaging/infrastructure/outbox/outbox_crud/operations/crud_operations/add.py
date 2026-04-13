"""Add event operations for outbox."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from messaging.infrastructure.outbox.outbox_crud._helpers import to_record
from python_outbox_core import IOutboxEvent

logger = logging.getLogger(__name__)


async def add_event_to_outbox(
    event: IOutboxEvent,
    session_factory: async_sessionmaker[AsyncSession],
    session: AsyncSession | None = None,
) -> None:
    """Store a serialized event in the provided or new session.

    For transactional outbox: pass an external session to commit atomically
    with business data. For standalone use: omit session to auto-commit.

    Args:
        event: The serialized event to store
        session_factory: SQLAlchemy async session factory
        session: External session for transactional outbox, or None to auto-commit
    """
    logger.debug("Adding event %s (type=%s) to outbox", event.event_id, event.event_type)

    if session is not None:
        session.add(to_record(event))
        logger.debug(
            "Event %s added to external session (caller controls commit)",
            event.event_id,
        )
    else:
        async with session_factory() as new_session:
            new_session.add(to_record(event))
            await new_session.commit()
        logger.debug("Event %s added to outbox and committed", event.event_id)
