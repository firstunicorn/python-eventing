"""Unit tests for Kafka publisher behavior."""

from __future__ import annotations

from typing import Any, cast

import pytest

from messaging.infrastructure.pubsub import KafkaEventPublisher
from tests.unit.infrastructure.conftest import FakeKafkaBroker, FakePublisher


def test_kafka_publisher_uses_event_type_as_topic() -> None:
    """Publisher should derive Kafka topic names from event type."""
    publisher = KafkaEventPublisher(cast(Any, FakePublisher()))
    topic = publisher._resolve_topic({"eventType": "gamification.XPAwarded"})

    assert topic == "gamification.XPAwarded"


@pytest.mark.asyncio
async def test_kafka_publisher_serializes_string_keys_to_bytes() -> None:
    """Publisher should encode string aggregate keys for FastStream Kafka."""
    broker = FakeKafkaBroker()
    publisher = KafkaEventPublisher(cast(Any, broker))
    message = {
        "eventType": "gamification.XPAwarded",
        "aggregateId": "user-123",
        "source": "gamification-service",
    }

    await publisher.publish_to_topic("gamification.XPAwarded", message)

    assert broker.published == [(message, "gamification.XPAwarded", b"user-123")]
