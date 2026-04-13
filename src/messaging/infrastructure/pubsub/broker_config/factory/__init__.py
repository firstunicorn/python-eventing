"""Kafka broker factory - re-exports."""

from messaging.infrastructure.pubsub.broker_config.factory.kafka_broker_factory import (
    create_kafka_broker,
)

__all__ = ["create_kafka_broker"]
