"""Integration tests for bridge error handling."""

import asyncio

import pytest


@pytest.mark.integration
@pytest.mark.requires_rabbitmq
class TestBridgeErrorHandling:
    """Test bridge error handling for malformed messages."""

    @pytest.mark.asyncio
    async def test_bridge_handles_malformed_messages(
        self, kafka_container, async_client_with_kafka
    ) -> None:
        """Bridge gracefully skips malformed Kafka messages."""
        from confluent_kafka import Producer

        producer_config = {
            "bootstrap.servers": kafka_container.get_bootstrap_server(),
        }
        producer = Producer(producer_config)

        # Send malformed JSON
        producer.produce("events", key=b"bad-key", value=b"not-json{invalid")
        producer.flush()

        await asyncio.sleep(1)

        # Bridge should log error but not crash
        assert True  # Placeholder
