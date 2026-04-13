"""Unit tests for processed message store validation and error handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from messaging.infrastructure.persistence.processed_message_store.duplicate_checker import (
    is_duplicate_claim,
)
from messaging.infrastructure.persistence.processed_message_store.processed_message_store import (
    SqlAlchemyProcessedMessageStore,
)


class TestSqlAlchemyProcessedMessageStoreValidation:
    """Test input validation for processed message store."""

    @pytest.mark.asyncio
    async def test_empty_consumer_name_raises_value_error(self) -> None:
        """Empty consumer_name should raise ValueError."""
        session = AsyncMock()
        store = SqlAlchemyProcessedMessageStore(session)

        with pytest.raises(ValueError, match="consumer_name must not be empty"):
            await store.claim(consumer_name="", event_id="evt-123")

        with pytest.raises(ValueError, match="consumer_name must not be empty"):
            await store.claim(consumer_name="   ", event_id="evt-123")

    @pytest.mark.asyncio
    async def test_empty_event_id_raises_value_error(self) -> None:
        """Empty event_id should raise ValueError."""
        session = AsyncMock()
        store = SqlAlchemyProcessedMessageStore(session)

        with pytest.raises(ValueError, match="event_id must not be empty"):
            await store.claim(consumer_name="test-consumer", event_id="")

        with pytest.raises(ValueError, match="event_id must not be empty"):
            await store.claim(consumer_name="test-consumer", event_id="   ")


class TestSqlAlchemyProcessedMessageStoreIntegrityErrors:
    """Test handling of database integrity errors."""

    @pytest.mark.asyncio
    async def test_non_duplicate_integrity_error_is_raised(self) -> None:
        """IntegrityErrors that are NOT duplicate claims should be raised."""
        session = MagicMock()
        # Mock synchronous methods (not async)
        session.in_nested_transaction = MagicMock(return_value=False)
        session.in_transaction = MagicMock(return_value=False)
        # Mock dialect for SQLAlchemy
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"  # Mock as SQLite database
        session.get_bind = MagicMock(return_value=mock_bind)
        # Mock async methods
        session.begin = AsyncMock()
        session.execute = AsyncMock()

        store = SqlAlchemyProcessedMessageStore(session)

        # Simulate a non-duplicate integrity error (e.g., foreign key violation)
        foreign_key_error = IntegrityError(
            statement="INSERT...",
            params={},
            orig=Exception("FOREIGN KEY constraint failed"),
        )
        session.execute.side_effect = foreign_key_error

        with pytest.raises(IntegrityError, match="FOREIGN KEY"):
            await store.claim(consumer_name="test-consumer", event_id="evt-123")


class TestIsDuplicateClaimFunction:
    """Test duplicate claim detection logic."""

    def test_detects_duplicate_keyword_in_error_message(self) -> None:
        """Error message containing 'duplicate' should return True."""
        error = IntegrityError(
            statement="INSERT...",
            params={},
            orig=Exception("DUPLICATE entry for key 'PRIMARY'"),
        )
        assert is_duplicate_claim(error) is True

    def test_detects_unique_keyword_in_error_message(self) -> None:
        """Error message containing 'unique' should return True."""
        error = IntegrityError(
            statement="INSERT...",
            params={},
            orig=Exception("UNIQUE constraint failed: processed_messages.event_id"),
        )
        assert is_duplicate_claim(error) is True

    def test_non_duplicate_error_returns_false(self) -> None:
        """Error without duplicate/unique keywords should return False."""
        error = IntegrityError(
            statement="INSERT...",
            params={},
            orig=Exception("FOREIGN KEY constraint failed"),
        )
        assert is_duplicate_claim(error) is False

    def test_handles_none_orig_attribute(self) -> None:
        """IntegrityError with None orig should check main error message."""
        error = IntegrityError(
            statement="INSERT...",
            params={},
            orig=None,
        )
        # IntegrityError.__str__() will be checked
        assert is_duplicate_claim(error) is False


class TestSqlAlchemyProcessedMessageStoreRowcount:
    """Test rowcount handling from database execution results."""

    @pytest.mark.asyncio
    async def test_returns_false_when_rowcount_is_zero(self) -> None:
        """Zero rowcount (no insert) should return False."""
        session = MagicMock()
        # Mock synchronous methods
        session.in_nested_transaction = MagicMock(return_value=False)
        session.in_transaction = MagicMock(return_value=False)
        # Mock dialect for SQLAlchemy
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)
        # Mock async methods
        session.begin = AsyncMock()

        store = SqlAlchemyProcessedMessageStore(session)

        # Mock result with rowcount=0
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute = AsyncMock(return_value=mock_result)

        result = await store.claim(consumer_name="test-consumer", event_id="evt-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_rowcount_is_none(self) -> None:
        """None rowcount should return False (defensive check)."""
        session = MagicMock()
        # Mock synchronous methods
        session.in_nested_transaction = MagicMock(return_value=False)
        session.in_transaction = MagicMock(return_value=False)
        # Mock dialect for SQLAlchemy
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)
        # Mock async methods
        session.begin = AsyncMock()

        store = SqlAlchemyProcessedMessageStore(session)

        # Mock result with rowcount=None
        mock_result = MagicMock()
        mock_result.rowcount = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await store.claim(consumer_name="test-consumer", event_id="evt-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_rowcount_is_positive(self) -> None:
        """Positive rowcount (successful insert) should return True."""
        session = MagicMock()
        # Mock synchronous methods
        session.in_nested_transaction = MagicMock(return_value=False)
        session.in_transaction = MagicMock(return_value=False)
        # Mock dialect for SQLAlchemy
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)
        # Mock async methods
        session.begin = AsyncMock()

        store = SqlAlchemyProcessedMessageStore(session)

        # Mock result with rowcount=1
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)

        result = await store.claim(consumer_name="test-consumer", event_id="evt-123")
        assert result is True


class TestSqlAlchemyProcessedMessageStoreTransactionHandling:
    """Test transaction state management."""

    @pytest.mark.asyncio
    async def test_starts_transaction_when_not_active(self) -> None:
        """Should call session.begin() when no transaction is active."""
        session = MagicMock()
        # No transaction active
        session.in_nested_transaction = MagicMock(return_value=False)
        session.in_transaction = MagicMock(return_value=False)
        # Mock dialect for SQLAlchemy
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)
        session.begin = AsyncMock()

        store = SqlAlchemyProcessedMessageStore(session)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)

        await store.claim(consumer_name="test-consumer", event_id="evt-123")

        # Verify session.begin() was called
        session.begin.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_begin_when_transaction_active(self) -> None:
        """Should NOT call session.begin() when transaction is already active."""
        session = MagicMock()
        # Transaction already active
        session.in_nested_transaction = MagicMock(return_value=False)
        session.in_transaction = MagicMock(return_value=True)
        # Mock dialect for SQLAlchemy
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)
        session.begin = AsyncMock()

        store = SqlAlchemyProcessedMessageStore(session)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)

        await store.claim(consumer_name="test-consumer", event_id="evt-123")

        # Verify session.begin() was NOT called
        session.begin.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_begin_when_nested_transaction_active(self) -> None:
        """Should NOT call session.begin() when nested transaction is active."""
        session = MagicMock()
        # Nested transaction active
        session.in_nested_transaction = MagicMock(return_value=True)
        session.in_transaction = MagicMock(return_value=False)
        # Mock dialect for SQLAlchemy
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)
        session.begin = AsyncMock()

        store = SqlAlchemyProcessedMessageStore(session)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)

        await store.claim(consumer_name="test-consumer", event_id="evt-123")

        # Verify session.begin() was NOT called
        session.begin.assert_not_awaited()
