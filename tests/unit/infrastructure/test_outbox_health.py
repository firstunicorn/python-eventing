"""Unit tests for outbox health check."""

from __future__ import annotations

from typing import Any, cast

import pytest

from messaging.infrastructure.health import EventingHealthCheck
from tests.unit.infrastructure.conftest import FakeBroker, FakeRepository


@pytest.mark.asyncio
async def test_health_check_reports_lag_degradation() -> None:
    """Health check should degrade when the outbox backlog is stale."""
    repository = FakeRepository()
    repository.pending_count = 5
    repository.oldest_age = 600.0
    health_check = EventingHealthCheck(
        cast(Any, repository),
        cast(Any, FakeBroker()),
        lag_threshold=2,
    )

    result = await health_check.check_health()

    assert result["checks"]["database"]["status"] == "healthy"
    assert result["checks"]["outbox"]["status"] == "degraded"
    assert result["status"] == "degraded"
