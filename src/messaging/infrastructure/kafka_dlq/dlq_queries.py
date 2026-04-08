"""DLQ query operations - queries outbox for failed events."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from messaging.infrastructure.persistence.orm_models.outbox_orm import (
    OutboxEventRecord,
)


class DLQQueries:
    """Query failed (dead-lettered) events from outbox table."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize DLQ queries with database session."""
        self._session = session

    async def list_failed_events(
        self,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, str]]:
        """List dead-lettered events from outbox where failed=True."""
        query = select(OutboxEventRecord).where(OutboxEventRecord.failed.is_(True))

        if event_type:
            query = query.where(OutboxEventRecord.event_type == event_type)

        query = query.order_by(OutboxEventRecord.failed_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(query)
        rows = result.scalars().all()

        return [
            {
                "id": row.event_id,
                "event_type": row.event_type,
                "failed_at": row.failed_at.isoformat() if row.failed_at else "",
                "error_message": row.error_message or "",
            }
            for row in rows
        ]

    async def get_by_id(self, event_id: str) -> OutboxEventRecord | None:
        """Get specific failed event from outbox by ID."""
        query = select(OutboxEventRecord).where(OutboxEventRecord.event_id == event_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
