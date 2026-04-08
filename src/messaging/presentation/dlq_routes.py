"""DLQ admin API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from messaging.infrastructure.kafka_dlq.dlq_admin_service import DLQAdminService
from messaging.infrastructure.kafka_dlq.dlq_queries import DLQQueries
from messaging.infrastructure.outbox.outbox_crud import OutboxCrudOperations
from messaging.infrastructure.persistence.dependencies import get_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/dlq", tags=["dlq"])


async def get_dlq_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DLQAdminService:
    """Dependency for DLQ admin service."""
    queries = DLQQueries(session)
    crud = OutboxCrudOperations(request.app.state.session_factory)
    return DLQAdminService(queries, crud)


@router.get("")
async def list_dlq_events(
    service: Annotated[DLQAdminService, Depends(get_dlq_service)],
    event_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, list[dict[str, str]]]:
    """List dead-lettered events from outbox where failed=True."""
    events = await service.list_failed_events(event_type, limit, offset)
    return {"events": events}


@router.post("/{message_id}/retry")
async def retry_dlq_event(
    message_id: str,
    service: Annotated[DLQAdminService, Depends(get_dlq_service)],
) -> dict[str, bool]:
    """Retry a dead-lettered event by resetting failed status."""
    try:
        await service.retry_event(message_id)
        return {"retried": True}
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e
