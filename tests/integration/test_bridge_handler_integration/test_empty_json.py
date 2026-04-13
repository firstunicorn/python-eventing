"""Test production handler empty JSON handling."""

import asyncio
import json

import pytest
from confluent_kafka import Producer

from .setup_helpers import initialize_production_bridge, setup_test_containers_config


@pytest.mark.integration
@pytest.mark.requires_kafka
@pytest.mark.requires_rabbitmq
class TestEmptyJSON:
    """Test production handler empty JSON handling."""

    @pytest.mark.asyncio
    async def test_production_handler_with_empty_json(
        self,
        kafka_container,
        rabbitmq_container,
        sqlite_session_factory,
        monkeypatch,
    ) -> None:
        """Test production handler gracefully handles empty JSON."""
        kafka_bootstrap, _, consumer_group_id = setup_test_containers_config(
            kafka_container,
            rabbitmq_container,
            monkeypatch,
            kafka_topic="events-empty-json-test",
        )

        _, async_session_factory = sqlite_session_factory

        broker, rabbit_broker = initialize_production_bridge(
            async_session_factory,
            consumer_group_id=consumer_group_id,
            kafka_topic="events-empty-json-test",
        )

        async with broker, rabbit_broker:
            await broker.start()
            await rabbit_broker.start()
            await asyncio.sleep(5)

            producer = Producer({"bootstrap.servers": kafka_bootstrap})
            producer.produce("events-empty-json-test", value=json.dumps({}).encode())
            producer.flush()

            await asyncio.sleep(8)
