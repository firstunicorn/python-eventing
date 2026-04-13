"""Kafka broker factory implementation.

Uses the Confluent backend (confluent-kafka-python) which is the open-source
Apache 2.0 licensed library, not the proprietary Confluent Platform.
"""

# mypy: disable-error-code="no-any-unimported,arg-type"

from faststream.confluent import KafkaBroker
from opentelemetry import trace
from prometheus_client import CollectorRegistry

from messaging.config import Settings
from messaging.core.contracts.circuit_breaker import CircuitBreaker
from messaging.infrastructure.pubsub.broker_config.factory.middleware_builder import (
    build_kafka_middlewares,
)


def create_kafka_broker(
    settings: Settings,
    prometheus_registry: CollectorRegistry | None = None,
    tracer_provider: trace.TracerProvider | None = None,
    circuit_breaker_threshold: int = 5,
    circuit_breaker_timeout: float = 30.0,
    enable_rate_limiter: bool = False,
    rate_limit_max_rate: int = 100,
    rate_limit_time_period: float = 1.0,
) -> KafkaBroker:
    """Create a Kafka broker configured with resilience and observability middlewares.

    Note:
        Consumer group configuration from settings.kafka_consumer_conf is passed at
        broker level via the 'config' parameter. Individual subscribers can override
        these defaults if needed.

    Args:
        settings: Application settings
        prometheus_registry: Optional Prometheus registry for metrics
        tracer_provider: Optional OpenTelemetry tracer provider for tracing
        circuit_breaker_threshold: Number of failures before circuit opens (default: 5)
        circuit_breaker_timeout: Seconds before half-open state (default: 30.0)
        enable_rate_limiter: Enable rate limiting middleware (default: False)
        rate_limit_max_rate: Maximum messages per time period (default: 100)
        rate_limit_time_period: Time period in seconds (default: 1.0)

    Returns:
        KafkaBroker: Configured FastStream Kafka broker with middlewares
    """
    shared_breaker = CircuitBreaker(
        failure_threshold=circuit_breaker_threshold,
        reset_timeout=circuit_breaker_timeout,
    )

    middlewares = build_kafka_middlewares(
        settings=settings,
        shared_breaker=shared_breaker,
        circuit_breaker_threshold=circuit_breaker_threshold,
        circuit_breaker_timeout=circuit_breaker_timeout,
        prometheus_registry=prometheus_registry,
        tracer_provider=tracer_provider,
        enable_rate_limiter=enable_rate_limiter,
        rate_limit_max_rate=rate_limit_max_rate,
        rate_limit_time_period=rate_limit_time_period,
    )

    return KafkaBroker(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=settings.kafka_client_id,
        enable_idempotence=True,
        config=settings.kafka_consumer_conf,
        middlewares=middlewares,
    )
