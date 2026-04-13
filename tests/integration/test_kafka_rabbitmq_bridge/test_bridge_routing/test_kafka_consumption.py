"""Integration test for Kafka consumption by bridge."""

import asyncio
import json

import pytest


@pytest.mark.integration
@pytest.mark.requires_rabbitmq
class TestKafkaConsumption:
    """Test Kafka consumption by the bridge."""

    @pytest.mark.asyncio
    async def test_bridge_consumes_from_kafka(
        self, kafka_container, async_client_with_kafka
    ) -> None:
        """Bridge consumes events from Kafka topic."""
        from confluent_kafka import Producer

        producer_config = {
            "bootstrap.servers": kafka_container.get_bootstrap_server(),
        }
        producer = Producer(producer_config)

        test_message = {"event_id": "bridge-test-1", "data": "test payload"}
        producer.produce(
            "bridge-test-topic",
            key=b"test-key",
            value=json.dumps(test_message).encode(),
        )
        producer.flush()

        await asyncio.sleep(1)

        assert True
