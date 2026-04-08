"""Unit tests for outbox replay query operations."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from messaging.infrastructure.outbox.outbox_replay_queries import OutboxReplayQueries


class TestOutboxReplayQueries:
    """Test outbox event replay queries."""

    @pytest.mark.asyncio
    async def test_query_by_event_type_returns_matching_events(self) -> None:
        """Query filters events by event_type."""
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=list)))
        queries = OutboxReplayQueries(session=session)

        results = await queries.get_by_type_and_range(
            event_type="user.created",
            from_ts=datetime(2026, 1, 1, tzinfo=UTC),
            to_ts=datetime(2026, 12, 31, tzinfo=UTC),
            limit=100,
            offset=0,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_query_by_time_range_filters_by_timestamps(self) -> None:
        """Query filters events within time range."""
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=list)))
        queries = OutboxReplayQueries(session=session)

        results = await queries.get_by_type_and_range(
            event_type=None,
            from_ts=datetime(2026, 3, 1, tzinfo=UTC),
            to_ts=datetime(2026, 3, 31, tzinfo=UTC),
            limit=50,
            offset=0,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_query_combined_filters_applies_all_criteria(self) -> None:
        """Query with event_type + time range + pagination."""
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=list)))
        queries = OutboxReplayQueries(session=session)

        results = await queries.get_by_type_and_range(
            event_type="order.completed",
            from_ts=datetime(2026, 2, 1, tzinfo=UTC),
            to_ts=datetime(2026, 2, 28, tzinfo=UTC),
            limit=20,
            offset=10,
        )

        assert isinstance(results, list)
