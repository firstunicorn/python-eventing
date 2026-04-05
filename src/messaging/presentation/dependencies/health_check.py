"""Health check dependency injection."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from messaging.infrastructure.health.outbox_health_check import EventingHealthCheck


async def get_outbox_health_check(request: Request) -> EventingHealthCheck:
    """Retrieve the outbox health check instance from app state.

    This dependency provides access to the EventingHealthCheck instance
    that was initialized during application lifespan. If the health check
    is not available (e.g., worker disabled), raises 503 Service Unavailable.

    Args:
        request (Request): The incoming FastAPI request object

    Returns:
        EventingHealthCheck: The initialized health check instance

    Raises:
        HTTPException: 503 if the health check infrastructure is not initialized
    """
    checker: EventingHealthCheck | None = getattr(
        request.app.state, "outbox_health_check", None
    )
    if checker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Outbox health check not initialized (worker may be disabled)",
        )
    return checker


OutboxHealthCheckDep = Annotated[EventingHealthCheck, Depends(get_outbox_health_check)]
