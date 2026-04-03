"""Integration tests for durable processed-message storage."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.integration.processed_message_consumers import FailingConsumer, RecordingConsumer


pytestmark = pytest.mark.asyncio


async def test_processed_message_store_blocks_duplicates_across_sessions(
    sqlite_session_factory: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    """Committed claims should block duplicates for fresh sessions and consumers."""
    _, session_factory = sqlite_session_factory
    message = {"eventId": "abc-123", "payload": 1}

    async with session_factory() as session:
        consumer = RecordingConsumer("gamification.learning", session)
        assert await consumer.consume(message) is True
        await session.commit()

    async with session_factory() as session:
        duplicate_consumer = RecordingConsumer("gamification.learning", session)
        assert await duplicate_consumer.consume(message) is False


async def test_processed_message_store_is_scoped_by_consumer_name(
    sqlite_session_factory: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    """Different consumer names should each claim the same event identifier once."""
    _, session_factory = sqlite_session_factory
    message = {"eventId": "abc-123", "payload": 1}

    async with session_factory() as session:
        learning = RecordingConsumer("gamification.learning", session)
        assessment = RecordingConsumer("gamification.assessment", session)
        assert await learning.consume(message) is True
        assert await assessment.consume(message) is True
        await session.commit()


async def test_rollback_releases_claim_for_retry(
    sqlite_session_factory: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    """Rolled-back claims should not block a later successful retry."""
    _, session_factory = sqlite_session_factory
    message = {"eventId": "abc-123", "payload": 1}

    async with session_factory() as session:
        consumer = FailingConsumer("gamification.learning", session)
        with pytest.raises(RuntimeError, match="boom"):
            await consumer.consume(message)
        await session.rollback()

    async with session_factory() as session:
        retry_consumer = RecordingConsumer("gamification.learning", session)
        assert await retry_consumer.consume(message) is True
        await session.commit()


async def test_commit_blocks_retry_after_success(
    sqlite_session_factory: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    """Committed successful claims should block later retries of the same message."""
    _, session_factory = sqlite_session_factory
    message = {"eventId": "abc-123", "payload": 1}

    async with session_factory() as session:
        consumer = RecordingConsumer("gamification.learning", session)
        assert await consumer.consume(message) is True
        await session.commit()

    async with session_factory() as session:
        duplicate_consumer = RecordingConsumer("gamification.learning", session)
        assert await duplicate_consumer.consume(message) is False
