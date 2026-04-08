"""Configuration for Kafka-to-RabbitMQ bridge."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BridgeConfig:
    """Configuration for bridge between Kafka and RabbitMQ."""

    kafka_topic: str
    rabbitmq_exchange: str
    routing_key_template: str  # e.g. "{event_type}" or "events.{aggregate_type}"
