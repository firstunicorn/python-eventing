"""Top-level router registration for the eventing service.

This module provides the `api_router` that exposes HTTP endpoints.
It includes liveness probes and the specialized `/health/outbox`
endpoint that reports on the underlying broker and database infrastructure.

See Also
--------
- messaging.infrastructure.health.outbox_health_check : Health checking logic
- messaging.presentation.dependencies : Dependency injection functions
- messaging.main : Where this router is included into the FastAPI app
"""

from typing import Any

from fastapi import APIRouter

from fastapi_middleware_toolkit import create_health_check_endpoint
from messaging.config import settings
from messaging.presentation.dependencies import OutboxHealthCheckDep

api_router = APIRouter()
_base_health = create_health_check_endpoint(settings.service_name)


@api_router.get("/health", tags=["health"], summary="Liveness probe")
async def health() -> dict[str, str]:
    """Return a basic service health payload."""
    payload = await _base_health()
    return {"status": "ok", "service": str(payload["service"])}


@api_router.get("/health/outbox", tags=["health"], summary="Outbox subsystem health")
async def outbox_health(checker: OutboxHealthCheckDep) -> dict[str, Any]:
    """Return outbox infrastructure health if it has been initialized."""
    return await checker.check_health()
