"""Integration tests for DLQ listing endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestDLQListing:
    """Test DLQ inspection endpoints."""

    @pytest.mark.asyncio
    async def test_get_dlq_returns_failed_events(self, async_client: AsyncClient) -> None:
        """GET /dlq returns list of dead-lettered events."""
        response = await async_client.get("/api/v1/dlq")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    @pytest.mark.asyncio
    async def test_get_dlq_filters_by_event_type(self, async_client: AsyncClient) -> None:
        """GET /dlq?event_type=X filters by type."""
        response = await async_client.get(
            "/api/v1/dlq",
            params={"event_type": "user.created"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        for event in data["events"]:
            assert event["event_type"] == "user.created"
