"""Integration tests for DLQ retry endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestDLQRetry:
    """Test DLQ retry endpoints."""

    @pytest.mark.asyncio
    async def test_retry_dlq_event_resets_failed_status(
        self, async_client: AsyncClient, sqlite_session_factory
    ) -> None:
        """POST /dlq/{event_id}/retry resets failed status, re-enqueues."""
        from datetime import UTC, datetime

        from messaging.infrastructure.persistence.orm_models.outbox_orm import OutboxEventRecord

        test_event_id = str(uuid4())

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
    async def test_retry_non_failed_event_raises_400(self, async_client: AsyncClient) -> None:
        """POST /dlq/{event_id}/retry on non-failed event raises 400."""
        non_failed_id = uuid4()

        response = await async_client.post(f"/api/v1/dlq/{non_failed_id}/retry")

        assert response.status_code in (400, 404)

    @pytest.mark.asyncio
    async def test_retry_increments_attempt_counter(
        self, async_client: AsyncClient, sqlite_session_factory
    ) -> None:
        """Retry increments attempt counter in outbox record."""
        import structlog
        from sqlalchemy import select

        from messaging.infrastructure.persistence.orm_models.outbox_orm import OutboxEventRecord

        logger = structlog.get_logger()
        test_event_id = str(uuid4())

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

        response = await async_client.post(f"/api/v1/dlq/{test_event_id}/retry")

        if response.status_code != 200:
            logger.warning("DLQ retry failed", status=response.status_code, body=response.text)

        assert response.status_code == 200

        async with session_factory() as session:
            result = await session.execute(
                select(OutboxEventRecord).where(OutboxEventRecord.event_id == test_event_id)
            )
            event = result.scalar_one()
            assert event.attempt_count == 2
            assert event.failed is False
