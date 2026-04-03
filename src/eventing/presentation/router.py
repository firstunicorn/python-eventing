"""Top-level router registration for the eventing service.

This module provides the `api_router` that exposes HTTP endpoints.
It includes liveness probes and the specialized `/health/outbox`
endpoint that reports on the underlying broker and database infrastructure.

See also
--------
- eventing.infrastructure.health.outbox_health_check : Health checking logic
- eventing.main : Where this router is included into the FastAPI app
"""

from typing import Any, cast

from fastapi import APIRouter, Request

from eventing.config import settings
from eventing.infrastructure.health.outbox_health_check import EventingHealthCheck
from fastapi_middleware_toolkit import create_health_check_endpoint

api_router = APIRouter()
_base_health = create_health_check_endpoint(settings.service_name)


@api_router.get("/health", tags=["health"], summary="Liveness probe")
async def health() -> dict[str, str]:
    """Return a basic service health payload."""
    payload = await _base_health()
    return {"status": "ok", "service": str(payload["service"])}


@api_router.get("/health/outbox", tags=["health"], summary="Outbox subsystem health")
async def outbox_health(request: Request) -> dict[str, Any]:
    """Return outbox infrastructure health if it has been initialized."""
    checker = cast(
        EventingHealthCheck | None,
        getattr(request.app.state, "outbox_health_check", None),
    )
    if checker is None:
        return {"status": "unavailable", "checks": {}}
    return await checker.check_health()
