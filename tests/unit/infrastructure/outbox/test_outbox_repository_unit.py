"""Unit tests for outbox repository facade."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository


class TestSqlAlchemyOutboxRepositoryDelegation:
    """Test that repository correctly delegates to CRUD and query operations."""

    @pytest.fixture
    def mock_session_factory(self) -> MagicMock:
        """Create mock session factory."""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_session_factory: MagicMock) -> SqlAlchemyOutboxRepository:
        """Create repository with mocked dependencies."""
        with (
            patch("messaging.infrastructure.outbox.outbox_repository.OutboxCrudOperations"),
            patch("messaging.infrastructure.outbox.outbox_repository.OutboxQueryOperations"),
        ):
            return SqlAlchemyOutboxRepository(mock_session_factory)

    @pytest.mark.asyncio
    async def test_add_event_delegates_to_crud(
        self, repository: SqlAlchemyOutboxRepository
    ) -> None:
        """add_event should delegate to CRUD operations."""
        mock_event = MagicMock()
        mock_session = AsyncMock()

        repository._crud.add_event = AsyncMock()

        await repository.add_event(mock_event, mock_session)

        repository._crud.add_event.assert_awaited_once_with(mock_event, mock_session)

    @pytest.mark.asyncio
    async def test_get_unpublished_returns_empty_list(
        self, repository: SqlAlchemyOutboxRepository
    ) -> None:
        """get_unpublished should return empty list (CDC handles publishing)."""
        result = await repository.get_unpublished(limit=100, offset=0)

        assert result == []
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_mark_published_delegates_to_crud(
        self, repository: SqlAlchemyOutboxRepository
    ) -> None:
        """mark_published should delegate to CRUD operations."""
        event_id = uuid4()

        repository._crud.mark_published = AsyncMock()

        await repository.mark_published(event_id)

        repository._crud.mark_published.assert_awaited_once_with(event_id)

    @pytest.mark.asyncio
    async def test_count_unpublished_delegates_to_queries(
        self, repository: SqlAlchemyOutboxRepository
    ) -> None:
        """count_unpublished should delegate to query operations."""
        repository._queries.count_unpublished = AsyncMock(return_value=42)

        result = await repository.count_unpublished()

        assert result == 42
        repository._queries.count_unpublished.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mark_failed_delegates_to_crud(
        self, repository: SqlAlchemyOutboxRepository
    ) -> None:
        """mark_failed should delegate to CRUD operations."""
        event_id = uuid4()
        error_message = "Test error"

        repository._crud.mark_failed = AsyncMock()

        await repository.mark_failed(event_id, error_message)

        repository._crud.mark_failed.assert_awaited_once_with(event_id, error_message)

    @pytest.mark.asyncio
    async def test_ping_delegates_to_queries(
        self, repository: SqlAlchemyOutboxRepository
    ) -> None:
        """ping should delegate to query operations."""
        repository._queries.ping = AsyncMock(return_value=True)

        result = await repository.ping()

        assert result is True
        repository._queries.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_oldest_unpublished_age_seconds_delegates_to_queries(
        self, repository: SqlAlchemyOutboxRepository
    ) -> None:
        """oldest_unpublished_age_seconds should delegate to query operations."""
        repository._queries.oldest_unpublished_age_seconds = AsyncMock(return_value=123.45)

        result = await repository.oldest_unpublished_age_seconds()

        assert result == 123.45
        repository._queries.oldest_unpublished_age_seconds.assert_awaited_once()
