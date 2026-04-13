"""Core outbox CRUD operations class."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from python_outbox_core import IOutboxEvent

from .add import add_event_to_outbox
from .status import mark_failed as mark_failed_helper
from .status import mark_published as mark_published_helper
from .status import reset_failed as reset_failed_helper

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
            event: The serialized event to store
            session: External session for transactional outbox, or None to auto-commit
        """
        await add_event_to_outbox(event, self._session_factory, session)

    async def mark_published(self, event_id: UUID) -> None:
        """Mark an event as published and timestamp the update."""
        await mark_published_helper(event_id, self._session_factory)

    async def mark_failed(self, event_id: UUID, error_message: str) -> None:
        """Persist failure state and error details for an event."""
        await mark_failed_helper(event_id, error_message, self._session_factory)

    async def reset_failed(self, event_id: UUID) -> None:
        """Reset failed event for retry: clear failed status, error, and increment attempt counter.

        Args:
            event_id: UUID of the failed event to reset
        """
        await reset_failed_helper(event_id, self._session_factory)
