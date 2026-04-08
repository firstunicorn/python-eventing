"""DLQ admin service for inspecting and retrying failed events."""

from uuid import UUID

from messaging.infrastructure.kafka_dlq.dlq_queries import DLQQueries
from messaging.infrastructure.outbox.outbox_crud import OutboxCrudOperations


class DLQAdminService:
    """Service for DLQ inspection and retry operations."""

    def __init__(
        self,
        queries: DLQQueries,
        crud: OutboxCrudOperations,
    ) -> None:
        """Initialize DLQ admin service."""
        self._queries = queries
        self._crud = crud

    async def list_failed_events(
        self,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, str]]:
        """List dead-lettered events from outbox."""
        return await self._queries.list_failed_events(event_type, limit, offset)

    async def retry_event(self, event_id: str) -> None:
        """Retry a specific dead-lettered event by resetting its failed status."""
        event = await self._queries.get_by_id(event_id)
        if not event:
            msg = f"Event {event_id} not found"
            raise ValueError(msg)

        if not event.failed:
            msg = f"Event {event_id} is not in failed status"
            raise ValueError(msg)

        await self._crud.reset_failed(UUID(event_id))
