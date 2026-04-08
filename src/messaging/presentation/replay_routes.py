"""HTTP API routes for event replay."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter

from messaging.presentation.dependencies.replay import ReplayServiceDep

router = APIRouter(prefix="/replay", tags=["replay"])


@router.get("")
async def query_replay_events(
    service: ReplayServiceDep,
    event_type: str | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Query events matching criteria without republishing.

    Args:
        service: Replay service dependency
        event_type: Optional event type filter
        from_ts: Start timestamp
        to_ts: End timestamp
        limit: Max results
        offset: Skip results

    Returns:
        dict with "events" list
    """
    if not from_ts or not to_ts:
        return {"events": [], "message": "from_ts and to_ts required"}

    events = await service.query(
        event_type=event_type,
        from_ts=from_ts,
        to_ts=to_ts,
        limit=limit,
        offset=offset,
    )

    return {
        "events": [
            {
                "id": e.id,
                "type": e.type,
                "data": e.data,
                "aggregate_id": e.aggregate_id,
                "aggregate_type": e.aggregate_type,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }


@router.post("")
async def replay_events(
    service: ReplayServiceDep,
    event_type: str | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    limit: int = 1000,
) -> dict[str, Any]:
    """Replay events matching criteria by republishing to Kafka.

    Args:
        service: Replay service dependency
        event_type: Optional event type filter
        from_ts: Start timestamp
        to_ts: End timestamp
        limit: Max events to replay

    Returns:
        dict with "replayed_count"
    """
    if not from_ts or not to_ts:
        return {"replayed_count": 0, "message": "from_ts and to_ts required"}

    count = await service.replay(
        event_type=event_type,
        from_ts=from_ts,
        to_ts=to_ts,
        limit=limit,
    )

    return {"replayed_count": count}
