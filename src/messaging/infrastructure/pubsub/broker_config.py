"""Factory for the FastStream Kafka broker using Confluent backend.

This module provides `create_kafka_broker`, a utility that builds and configures
a FastStream `KafkaBroker` instance using the application settings with native
observability middlewares (Prometheus, OpenTelemetry) and resilience (CircuitBreaker).

IMPORTANT: This uses faststream[confluent], which wraps the open-source
confluent-kafka-python library (Apache 2.0 licensed). This is NOT the proprietary
Confluent Platform - just the open source librdkafka-based Python client.

See Also
--------
- messaging.config.Settings : The application settings
- messaging.infrastructure.pubsub.kafka_publisher : The publisher that uses this broker
- confluent-kafka-python: https://github.com/confluentinc/confluent-kafka-python
"""

# mypy: disable-error-code="no-any-unimported,arg-type"

from typing import Any

from faststream.confluent import KafkaBroker
from faststream.confluent.opentelemetry import KafkaTelemetryMiddleware
from faststream.confluent.prometheus import KafkaPrometheusMiddleware
from opentelemetry import trace
from prometheus_client import CollectorRegistry

from messaging.config import Settings
from messaging.core.contracts.circuit_breaker import CircuitBreaker
from messaging.infrastructure.resilience.circuit_breaker_middleware import (
    CircuitBreakerMiddleware,
)
from messaging.infrastructure.resilience.rate_limiter_middleware import (
    RateLimiterMiddleware,
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

    Uses the Confluent backend (confluent-kafka-python) which supports broker-level
    consumer group configuration via the 'config' parameter. This is the open-source
    Apache 2.0 licensed library, not the proprietary Confluent Platform.

    Middlewares are applied in order:
    1. Circuit Breaker (resilience) - Protects against cascading failures
    2. Rate Limiter (optional resilience) - Throttles message consumption
    3. Prometheus (metrics) - Collects broker metrics
    4. OpenTelemetry (tracing) - Distributed tracing

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
    middlewares: list[Any] = []

    # Add Circuit Breaker middleware first (resilience layer)
    # Create a shared circuit breaker instance that persists across middleware calls
    shared_breaker = CircuitBreaker(
        failure_threshold=circuit_breaker_threshold,
        reset_timeout=circuit_breaker_timeout,
    )
    
    # FastStream requires a factory function that accepts (msg, context) and returns middleware
    def circuit_breaker_factory(msg: Any = None, context: Any = None) -> CircuitBreakerMiddleware:
        # Return middleware with the SHARED circuit breaker
        middleware = CircuitBreakerMiddleware(
            failure_threshold=circuit_breaker_threshold,
            reset_timeout=circuit_breaker_timeout,
        )
        # Replace the middleware's circuit breaker with the shared one
        middleware._breaker = shared_breaker
        return middleware
    
    middlewares.append(circuit_breaker_factory)

    # Add Rate Limiter middleware if enabled
    if enable_rate_limiter:
        middlewares.append(
            RateLimiterMiddleware(
                max_rate=rate_limit_max_rate,
                time_period=rate_limit_time_period,
            )
        )

    # Add Prometheus middleware if registry provided
    if prometheus_registry is not None:
        middlewares.append(
            KafkaPrometheusMiddleware(
                registry=prometheus_registry,
                app_name=settings.service_name,
            )
        )

    # Add OpenTelemetry middleware if tracer provider provided
    if tracer_provider is not None:
        middlewares.append(
            KafkaTelemetryMiddleware(
                tracer_provider=tracer_provider,
            )
        )

    return KafkaBroker(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=settings.kafka_client_id,
        enable_idempotence=True,
        config=settings.kafka_consumer_conf,
        middlewares=middlewares,
    )
