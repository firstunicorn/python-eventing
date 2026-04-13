"""Kafka-to-RabbitMQ bridge configuration initialization."""

from messaging.config import settings
from messaging.infrastructure.pubsub.bridge.config import BridgeConfig


def initialize_bridge_config() -> BridgeConfig:
    """Initialize Kafka-to-RabbitMQ bridge configuration.

    Returns:
        BridgeConfig: Bridge configuration
    """
    return BridgeConfig(
        kafka_topic="events",
        rabbitmq_exchange=settings.rabbitmq_exchange,
        routing_key_template="{event_type}",
        consumer_group_id="eventing-consumers",
    )
