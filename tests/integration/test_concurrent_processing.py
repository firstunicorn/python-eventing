"""Concurrent processing and claim race tests."""

from __future__ import annotations

import asyncio

import pytest

from messaging.infrastructure.persistence.processed_message_store.processed_message_store import (
    SqlAlchemyProcessedMessageStore,
)

pytestmark = pytest.mark.asyncio


async def test_concurrent_claim_same_consumer_one_succeeds(
    sqlite_session_factory: tuple,
) -> None:
    """Only one claim should succeed when two concurrent calls race."""
    engine, factory = sqlite_session_factory
    async with factory() as session:
        store = SqlAlchemyProcessedMessageStore(session)
        consumer_name = "worker-a"
        event_id = "evt-race-001"

        async def try_claim() -> bool:
            return await store.claim(consumer_name=consumer_name, event_id=event_id)

        results = await asyncio.gather(try_claim(), try_claim())
        await session.commit()
    assert results.count(True) == 1
    assert results.count(False) == 1


async def test_concurrent_claim_different_consumers_both_succeed(
    sqlite_session_factory: tuple,
) -> None:
    """Different consumer names should each be able to claim."""
    engine, factory = sqlite_session_factory
    async with factory() as session:
        store = SqlAlchemyProcessedMessageStore(session)
        event_id = "evt-race-002"

        async def try_claim(name: str) -> bool:
            return await store.claim(consumer_name=name, event_id=event_id)

        results = await asyncio.gather(
            try_claim("worker-a"),
            try_claim("worker-b"),
        )
        await session.commit()
    assert results == [True, True]
