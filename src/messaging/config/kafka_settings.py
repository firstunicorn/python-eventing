"""Kafka-specific configuration settings."""

from pydantic import BaseModel, Field


class KafkaSettings(BaseModel):
    """Kafka broker configuration settings."""

    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers for the event broker.",
    )
    kafka_client_id: str = Field(default="eventing", description="Kafka client identifier.")
    kafka_consumer_conf: dict[str, str] = Field(
        default_factory=lambda: {
            "group.id": "eventing-consumers",
            "partition.assignment.strategy": "cooperative-sticky",
            "max.poll.interval.ms": "300000",
            "session.timeout.ms": "45000",
            "heartbeat.interval.ms": "15000",
        },
        description=(
            "Kafka consumer group configuration for confluent-kafka-python (open source). "
            "Passed to KafkaBroker via 'config' parameter. Uses librdkafka configuration format. "
            "See: https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md"
        ),
    )
    rate_limiter_enabled: bool = Field(
        default=False, description="Enable rate limiting middleware for message consumption"
    )
    rate_limiter_max_rate: int = Field(
        default=100, description="Maximum number of messages to process per time period"
    )
    rate_limiter_time_period: float = Field(
        default=1.0, description="Time period in seconds for rate limiting"
    )
