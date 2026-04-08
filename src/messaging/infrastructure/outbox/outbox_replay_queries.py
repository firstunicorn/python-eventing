"""Query operations for event replay from outbox."""

from datetime import datetime

from python_outbox_core.events import IOutboxEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from messaging.core.contracts.base_event import BaseEvent
from messaging.infrastructure.persistence.orm_models.outbox_orm import (
    OutboxEventRecord,
)


class OutboxReplayQueries:
    """Query outbox events for replay by type and time range."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with async database session."""
        self._session = session

    async def get_by_type_and_range(  # type: ignore[no-any-unimported]
        self,
        event_type: str | None,
        from_ts: datetime,
        to_ts: datetime,
        limit: int,
        offset: int,
    ) -> list[IOutboxEvent]:
        """Query outbox events matching criteria.

        Args:
            event_type: Optional event type filter (e.g., 'user.created')
            from_ts: Start timestamp (inclusive)
            to_ts: End timestamp (inclusive)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of outbox events matching criteria
        """
        query = select(OutboxEventRecord).where(
            OutboxEventRecord.created_at >= from_ts,
            OutboxEventRecord.created_at <= to_ts,
        )

        if event_type:
            query = query.where(OutboxEventRecord.event_type == event_type)

        query = query.order_by(OutboxEventRecord.created_at).limit(limit).offset(offset)

        result = await self._session.execute(query)
        rows = result.scalars().all()

        return [BaseEvent.model_validate(row.payload) for row in rows]
