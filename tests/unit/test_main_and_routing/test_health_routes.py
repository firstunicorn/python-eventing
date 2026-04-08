"""Tests for health route endpoints."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from messaging.presentation.router import outbox_health
from tests.unit.test_main_and_routing.test_fixtures import DummyChecker


@pytest.mark.asyncio
async def test_outbox_health_returns_unavailable_without_checker() -> None:
    """Route should raise 503 when lifespan has not set a checker."""
    from fastapi import HTTPException

    from messaging.presentation.dependencies import get_outbox_health_check

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    with pytest.raises(HTTPException) as exc_info:
        await get_outbox_health_check(request)  # type: ignore[arg-type] # Mock Request type compatibility with FastAPI

    assert exc_info.value.status_code == 503
    assert "not initialized" in exc_info.value.detail


@pytest.mark.asyncio
async def test_outbox_health_uses_checker_when_present() -> None:
    """Route should delegate to the configured checker."""

    result = await outbox_health(checker=DummyChecker())  # type: ignore[arg-type] # DummyChecker implements IOutboxHealthCheck protocol

    assert result["status"] == "healthy"
