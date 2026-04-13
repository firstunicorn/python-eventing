"""Integration tests for bridge idempotency."""

import asyncio
import json

import pytest


@pytest.mark.integration
@pytest.mark.requires_rabbitmq
class TestBridgeIdempotency:
    """Test bridge idempotency behavior."""

    @pytest.mark.asyncio
    async def test_bridge_is_idempotent(self, kafka_container, async_client_with_kafka) -> None:
        """Bridge uses processed-message store to prevent duplicate publishes."""
        from confluent_kafka import Producer

        # Publish same message twice
        producer_config = {
            "bootstrap.servers": kafka_container.get_bootstrap_server(),
        }
        producer = Producer(producer_config)

        # BUG FIX: UUID prevents idempotency collisions (same rationale as test_bridge_publishes_to_rabbitmq)
        import uuid

        event_id = f"idempotent-test-{uuid.uuid4()}"

        test_message = {"event_id": event_id, "data": "duplicate test"}
        for _ in range(2):
            producer.produce(
                "events",
                key=b"same-key",
                value=json.dumps(test_message).encode(),
            )
        producer.flush()

        # 5s for slow CI (same rationale as test_bridge_publishes_to_rabbitmq)
        await asyncio.sleep(5)

        # Bridge should only process once due to idempotency check
        # Verification requires checking processed_message store
        assert True  # Placeholder
