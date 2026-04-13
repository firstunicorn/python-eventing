"""Middleware configuration for Kafka broker."""

from typing import Any

from faststream.confluent.opentelemetry import KafkaTelemetryMiddleware
from faststream.confluent.prometheus import KafkaPrometheusMiddleware
from opentelemetry import trace
from prometheus_client import CollectorRegistry

from messaging.config import Settings
from messaging.core.contracts.circuit_breaker import CircuitBreaker
from messaging.infrastructure.pubsub.broker_config._factory_helpers import (
    create_circuit_breaker_factory,
)
from messaging.infrastructure.resilience.rate_limiter_middleware import RateLimiterMiddleware


def build_kafka_middlewares(
    settings: Settings,
    shared_breaker: CircuitBreaker,
    circuit_breaker_threshold: int,
    circuit_breaker_timeout: float,
    prometheus_registry: CollectorRegistry | None,
    tracer_provider: trace.TracerProvider | None,
    enable_rate_limiter: bool,
    rate_limit_max_rate: int,
    rate_limit_time_period: float,
) -> list[Any]:
    """Build middleware stack for Kafka broker.

    Middlewares are applied in order:
    1. Circuit Breaker (resilience) - Protects against cascading failures
    2. Rate Limiter (optional resilience) - Throttles message consumption
    3. Prometheus (metrics) - Collects broker metrics
    4. OpenTelemetry (tracing) - Distributed tracing

    Args:
        settings: Application settings
        shared_breaker: Shared circuit breaker instance
        circuit_breaker_threshold: Number of failures before circuit opens
        circuit_breaker_timeout: Seconds before half-open state
        prometheus_registry: Optional Prometheus registry for metrics
        tracer_provider: Optional OpenTelemetry tracer provider for tracing
        enable_rate_limiter: Enable rate limiting middleware
        rate_limit_max_rate: Maximum messages per time period
        rate_limit_time_period: Time period in seconds

    Returns:
        List of configured middleware instances
    """
    middlewares: list[Any] = []

    circuit_breaker_factory = create_circuit_breaker_factory(
        shared_breaker=shared_breaker,
        circuit_breaker_threshold=circuit_breaker_threshold,
        circuit_breaker_timeout=circuit_breaker_timeout,
    )
    middlewares.append(circuit_breaker_factory)

    if enable_rate_limiter:
        middlewares.append(
            RateLimiterMiddleware(
                max_rate=rate_limit_max_rate,
                time_period=rate_limit_time_period,
            )
        )

    if prometheus_registry is not None:
        middlewares.append(
            KafkaPrometheusMiddleware(
                registry=prometheus_registry,
                app_name=settings.service_name,
            )
        )

    if tracer_provider is not None:
        middlewares.append(
            KafkaTelemetryMiddleware(
                tracer_provider=tracer_provider,
            )
        )

    return middlewares
