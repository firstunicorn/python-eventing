"""Factory for the FastStream Kafka broker.

This module provides `create_kafka_broker`, a utility that builds and configures
a FastStream `KafkaBroker` instance using the application settings.

See also
--------
- eventing.config.Settings : The application settings
- eventing.infrastructure.messaging.kafka_publisher : The publisher that uses this broker
"""

from faststream.kafka import KafkaBroker

from eventing.config import Settings


def create_kafka_broker(settings: Settings) -> KafkaBroker:
    """Create a Kafka broker configured for idempotent publishing."""
    return KafkaBroker(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=settings.kafka_client_id,
        enable_idempotence=True,
    )
