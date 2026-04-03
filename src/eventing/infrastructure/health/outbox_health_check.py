"""Health check adapter for outbox and broker infrastructure.

This module provides `EventingHealthCheck`, which aggregates health signals from
the database, the Kafka broker, and the outbox worker's lag metrics. It helps
ensure that the event publishing pipeline is healthy and events aren't piling up.

See also
--------
- eventing.infrastructure.health : The health check namespace
- eventing.infrastructure.outbox.outbox_repository : Used to measure outbox lag
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from faststream.kafka import KafkaBroker

from eventing.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from python_outbox_core.health_check import HealthStatus, OutboxHealthCheck


class EventingHealthCheck(OutboxHealthCheck):
    """Aggregate database, broker, and outbox lag health signals."""

    def __init__(
        self,
        repository: SqlAlchemyOutboxRepository,
        broker: KafkaBroker,
        lag_threshold: int = 1000,
        stale_after_seconds: int = 300,
    ) -> None:
        self._repository = repository
        self._broker = broker
        self._lag_threshold = lag_threshold
        self._stale_after_seconds = stale_after_seconds

    async def check_health(self) -> dict[str, Any]:
        """Return a combined health payload for the outbox subsystem."""
        checks = {
            "database": await self.check_database(),
            "broker": await self.check_broker(),
            "outbox": await self.check_outbox_lag(),
        }
        statuses = {check["status"] for check in checks.values()}
        status = (
            HealthStatus.HEALTHY
            if statuses == {HealthStatus.HEALTHY}
            else HealthStatus.DEGRADED
        )
        if HealthStatus.UNHEALTHY in statuses:
            status = HealthStatus.UNHEALTHY
        return {
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": checks,
        }

    async def check_database(self) -> dict[str, Any]:
        """Check whether the repository database can answer a ping."""
        try:
            await self._repository.ping()
            return {"status": HealthStatus.HEALTHY}
        except Exception as exc:
            return {"status": HealthStatus.UNHEALTHY, "error": str(exc)}

    async def check_broker(self) -> dict[str, Any]:
        """Check whether the Kafka broker is reachable."""
        try:
            healthy = await self._broker.ping(1.0)
        except Exception as exc:
            return {"status": HealthStatus.UNHEALTHY, "error": str(exc)}
        status = HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
        return {"status": status}

    async def check_outbox_lag(self) -> dict[str, Any]:
        """Report unpublished count and age of the oldest pending event."""
        pending_count = await self._repository.count_unpublished()
        oldest_age = await self._repository.oldest_unpublished_age_seconds()
        status = HealthStatus.HEALTHY
        if pending_count > self._lag_threshold or oldest_age > self._stale_after_seconds:
            status = HealthStatus.DEGRADED
        return {
            "status": status,
            "pending_count": pending_count,
            "oldest_event_age_seconds": round(oldest_age, 2),
        }
