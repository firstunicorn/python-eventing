"""Testcontainer fixtures for Kafka and RabbitMQ."""

import os
import time

import pytest


@pytest.fixture(scope="session")
def docker_or_skip() -> None:
    """Skip container-based tests when Docker is not available."""
    from .config import _docker_available

    if not _docker_available():
        pytest.skip("Docker is unavailable in this environment")


@pytest.fixture(scope="session")
def kafka_container(docker_or_skip):
    """Provide a Kafka container for integration tests using Testcontainers."""
    from testcontainers.kafka import KafkaContainer

    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")
    kafka.start(timeout=300)

    yield kafka

    kafka.stop()


@pytest.fixture(scope="session")
def rabbitmq_container(docker_or_skip):
    """Provide a RabbitMQ container for integration tests using Testcontainers."""
    from testcontainers.rabbitmq import RabbitMqContainer

    os.environ["TC_HOST"] = "localhost"
    os.environ["TESTCONTAINERS_WAIT_TIMEOUT"] = "300"

    rabbitmq = RabbitMqContainer(
        "rabbitmq:3-management",
        username="testuser",
        password="testpass",  # noqa: S106
    )

    with rabbitmq:
        time.sleep(30)
        yield rabbitmq
