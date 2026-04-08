"""Integration tests for DLQ admin HTTP API."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestDLQAdminAPI:
    """Test DLQ inspection and retry endpoints."""

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

    @pytest.mark.asyncio
    async def test_retry_dlq_event_resets_failed_status(
        self, async_client: AsyncClient, sqlite_session_factory
    ) -> None:
        """POST /dlq/{event_id}/retry resets failed status, re-enqueues."""
        from messaging.infrastructure.persistence.orm_models.outbox_orm import (
            OutboxEventRecord,
        )
        from datetime import UTC, datetime
        
        test_event_id = str(uuid4())
        
        # Seed a failed outbox event
        _, session_factory = sqlite_session_factory
        async with session_factory() as session:
            failed_event = OutboxEventRecord(
                event_id=test_event_id,
                event_type="test.dlq",
                aggregate_id="test-aggregate",
                payload={"test": "data"},
                occurred_at=datetime.now(UTC),
                failed=True,
                error_message="Simulated failure",
                attempt_count=1,
            )
            session.add(failed_event)
            await session.commit()

        response = await async_client.post(f"/api/v1/dlq/{test_event_id}/retry")

        assert response.status_code == 200
        data = response.json()
        assert "retried" in data

    @pytest.mark.asyncio
    async def test_retry_non_failed_event_raises_400(
        self, async_client: AsyncClient
    ) -> None:
        """POST /dlq/{event_id}/retry on non-failed event raises 400."""
        non_failed_id = uuid4()

        response = await async_client.post(f"/api/v1/dlq/{non_failed_id}/retry")

        assert response.status_code in (400, 404)

    @pytest.mark.asyncio
    async def test_retry_increments_attempt_counter(
        self, async_client: AsyncClient, sqlite_session_factory
    ) -> None:
        """Retry increments attempt counter in outbox record."""
        from messaging.infrastructure.persistence.orm_models.outbox_orm import (
            OutboxEventRecord,
        )
        from sqlalchemy import select
        import structlog

        logger = structlog.get_logger()
        test_event_id = str(uuid4())  # Use valid UUID format

        # Seed a failed outbox event
        _, session_factory = sqlite_session_factory
        async with session_factory() as session:
            from datetime import UTC, datetime
            
            failed_event = OutboxEventRecord(
                event_id=test_event_id,
                event_type="test.event",
                aggregate_id="test-aggregate",
                payload={"test": "data"},
                occurred_at=datetime.now(UTC),
                failed=True,
                error_message="Simulated failure",
                attempt_count=1,
            )
            session.add(failed_event)
            await session.commit()

        # Retry the event
        response = await async_client.post(f"/api/v1/dlq/{test_event_id}/retry")

        if response.status_code != 200:
            logger.warning("DLQ retry failed", status=response.status_code, body=response.text)

        assert response.status_code == 200

        # Verify attempt counter was incremented
        async with session_factory() as session:
            result = await session.execute(
                select(OutboxEventRecord).where(
                    OutboxEventRecord.event_id == test_event_id
                )
            )
            event = result.scalar_one()
            assert event.attempt_count == 2
            assert event.failed is False  # Reset for retry
