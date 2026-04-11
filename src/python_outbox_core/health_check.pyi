from enum import StrEnum
from typing import Any

# pylint: disable=too-many-ancestors

class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class OutboxHealthCheck:
    async def check_health(self) -> dict[str, Any]: ...
