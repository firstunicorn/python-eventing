"""Pytest fixtures for consumer group configuration tests."""

import asyncio

import pytest
from confluent_kafka.admin import (  # type: ignore[attr-defined]
    AdminClient,
    NewTopic,
)


@pytest.fixture
async def kafka_with_partitions(kafka_container):
    """Create Kafka topics with multiple partitions for consumer group tests."""
    admin_config = {"bootstrap.servers": kafka_container.get_bootstrap_server()}
    admin_client = AdminClient(admin_config)

    topics = [NewTopic("multi-partition-topic", num_partitions=4, replication_factor=1)]
    admin_client.create_topics(topics)

    await asyncio.sleep(2)

    return kafka_container.get_bootstrap_server()
