"""Health degradation status transitions and lag threshold testing."""

from __future__ import annotations

from typing import Any, cast

import pytest

from messaging.infrastructure.health import EventingHealthCheck
from tests.unit.infrastructure.conftest import FakeBroker, FakeRepository

pytestmark = pytest.mark.asyncio


async def test_health_ok_when_no_backlog() -> None:
    repo = FakeRepository()
    repo.pending_count = 0
    repo.oldest_age = 0.0
    checker = EventingHealthCheck(
        cast(Any, repo),
        cast(Any, FakeBroker(healthy=True)),
        lag_threshold=10,
        stale_after_seconds=300,
    )
    result = await checker.check_health()
    assert result["status"] == "healthy"
    assert result["checks"]["outbox"]["pending_count"] == 0


async def test_health_degraded_when_pending_exceeds_threshold() -> None:
    repo = FakeRepository()
    repo.pending_count = 15
    repo.oldest_age = 60.0
    checker = EventingHealthCheck(
        cast(Any, repo),
        cast(Any, FakeBroker(healthy=True)),
        lag_threshold=10,
        stale_after_seconds=300,
    )
    result = await checker.check_health()
    assert result["status"] == "degraded"
    outbox = result["checks"]["outbox"]
    assert outbox["pending_count"] == 15
    assert outbox["status"] == "degraded"


async def test_health_degraded_when_stale_event() -> None:
    repo = FakeRepository()
    repo.pending_count = 1
    repo.oldest_age = 500.0
    checker = EventingHealthCheck(
        cast(Any, repo),
        cast(Any, FakeBroker(healthy=True)),
        lag_threshold=100,
        stale_after_seconds=300,
    )
    result = await checker.check_health()
    assert result["status"] == "degraded"
    assert result["checks"]["outbox"]["pending_count"] == 1
    assert result["checks"]["outbox"]["oldest_event_age_seconds"] == 500.0


async def test_health_unhealthy_when_broker_down() -> None:
    repo = FakeRepository()
    repo.pending_count = 0
    repo.oldest_age = 0.0
    checker = EventingHealthCheck(
        cast(Any, repo),
        cast(Any, FakeBroker(healthy=False)),
        lag_threshold=10,
        stale_after_seconds=300,
    )
    result = await checker.check_health()
    assert result["status"] == "unhealthy"
