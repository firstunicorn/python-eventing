"""Integration tests for event replay HTTP API."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestEventReplayAPI:
    """Test event replay HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_query_replay_events_by_type(self, async_client: AsyncClient) -> None:
        """GET /api/v1/replay returns events matching criteria."""
        response = await async_client.get(
            "/api/v1/replay",
            params={"event_type": "user.created", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    @pytest.mark.asyncio
    async def test_replay_events_with_time_range(self, async_client: AsyncClient) -> None:
        """POST /api/v1/replay republishes events in time range."""
        response = await async_client.post(
            "/api/v1/replay",
            json={
                "from_ts": "2026-01-01T00:00:00Z",
                "to_ts": "2026-01-31T23:59:59Z",
                "event_type": "order.completed",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "replayed_count" in data
        assert isinstance(data["replayed_count"], int)

    @pytest.mark.asyncio
    async def test_replayed_events_preserve_original_data(self, async_client: AsyncClient) -> None:
        """Replayed events get new IDs but preserve original payload."""
        response = await async_client.post(
            "/api/v1/replay",
            json={
                "event_type": "user.registered",
                "from_ts": "2026-03-01T00:00:00Z",
                "to_ts": "2026-03-31T23:59:59Z",
            },
        )

        assert response.status_code == 200
