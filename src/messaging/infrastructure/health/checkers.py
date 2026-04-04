"""Health checkers for database, broker, and outbox lag.

Extracted functions for individual health checks, preserving full logging and
error-handling behavior from the original EventingHealthCheck class.
"""

from __future__ import annotations

import logging
from typing import Any

from faststream.kafka import KafkaBroker

from python_outbox_core.health_check import HealthStatus

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


async def check_database(repository: Any) -> dict[str, Any]:
    """Check whether the repository database can answer a ping."""
    try:
        await repository.ping()
        logger.debug("Database health check passed")
        return {"status": HealthStatus.HEALTHY}
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc, exc_info=True)
        return {"status": HealthStatus.UNHEALTHY, "error": str(exc)}


async def check_broker(broker: KafkaBroker) -> dict[str, Any]:
    """Check whether the Kafka broker is reachable."""
    try:
        healthy = await broker.ping(1.0)
    except Exception as exc:
        logger.warning("Broker health check failed: %s", exc, exc_info=True)
        return {"status": HealthStatus.UNHEALTHY, "error": str(exc)}
    status = HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
    if status == HealthStatus.HEALTHY:
        logger.debug("Broker health check passed")
    else:
        logger.warning("Broker health check failed: ping returned false")
    return {"status": status}


async def check_outbox_lag(
    repository: Any,
    *,
    lag_threshold: int,
    stale_after_seconds: int,
) -> dict[str, Any]:
    """Report unpublished count and age of the oldest pending event."""
    pending_count = await repository.count_unpublished()
    oldest_age = await repository.oldest_unpublished_age_seconds()
    status = HealthStatus.HEALTHY
    if pending_count > lag_threshold or oldest_age > stale_after_seconds:
        status = HealthStatus.DEGRADED
        logger.warning(
            "Outbox lag detected: pending_count=%d (threshold=%d), oldest_age=%.2fs (threshold=%ds)",
            pending_count, lag_threshold, oldest_age, stale_after_seconds,
        )
    else:
        logger.debug("Outbox lag check passed: pending_count=%d, oldest_age=%.2fs", pending_count, oldest_age)
    return {
        "status": status,
        "pending_count": pending_count,
        "oldest_event_age_seconds": round(oldest_age, 2),
    }
