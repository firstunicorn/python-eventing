"""Pytest fixtures for circuit breaker chaos tests."""

import pytest


@pytest.fixture
async def kafka_for_chaos(docker_or_skip):
    """Create a Kafka container that can be stopped/restarted during chaos tests."""
    from testcontainers.kafka import KafkaContainer

    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")
    kafka.start(timeout=300)

    yield kafka

    try:
        kafka.stop()
    except Exception:
        pass


@pytest.fixture
async def kafka_broker_with_circuit_breaker(kafka_for_chaos):
    """Create Kafka broker with circuit breaker for chaos testing."""
    import asyncio

    from messaging.config import Settings
    from messaging.infrastructure.pubsub.broker_config import create_kafka_broker

    settings = Settings(
        kafka_bootstrap_servers=kafka_for_chaos.get_bootstrap_server(),
        kafka_client_id="chaos-test-client",
    )

    broker = create_kafka_broker(
        settings=settings,
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=2.0,
    )

    await broker.connect()
    await broker.start()

    await asyncio.sleep(1)

    yield broker, kafka_for_chaos

    await broker.stop()
