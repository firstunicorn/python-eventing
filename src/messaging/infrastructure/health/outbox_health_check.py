"""Health check adapter for outbox and broker infrastructure.

This module provides `EventingHealthCheck`, which aggregates health signals from
the database, the Kafka broker, and the outbox worker's lag metrics. It helps
ensure that the event publishing pipeline is healthy and events aren't piling up.

See also
--------
- messaging.infrastructure.health : The health check namespace
- messaging.infrastructure.outbox.outbox_repository : Used to measure outbox lag
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from faststream.kafka import KafkaBroker

from messaging.infrastructure.health.checkers import check_broker, check_database, check_outbox_lag
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from python_outbox_core.health_check import HealthStatus, OutboxHealthCheck

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


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
            "database": await check_database(self._repository),
            "broker": await check_broker(self._broker),
            "outbox": await check_outbox_lag(
                self._repository,
                lag_threshold=self._lag_threshold,
                stale_after_seconds=self._stale_after_seconds,
            ),
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
