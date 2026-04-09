"""Unit tests for broker configuration and middleware wiring."""

import pytest
from prometheus_client import CollectorRegistry

from messaging.config import Settings
from messaging.infrastructure.pubsub.broker_config import create_kafka_broker
from messaging.infrastructure.resilience.rate_limiter_middleware import (
    RateLimiterMiddleware,
)


class TestCreateKafkaBroker:
    """Test broker middleware configuration."""

    def test_broker_without_rate_limiter_has_two_middlewares(self) -> None:
        """Broker has 2 middlewares when rate limiter disabled."""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            rate_limiter_enabled=False,
        )
        registry = CollectorRegistry()
        
        broker = create_kafka_broker(
            settings,
            prometheus_registry=registry,
            enable_rate_limiter=False,
        )
        
        # Circuit breaker + Prometheus + (no Telemetry since no tracer)
        assert len(broker.middlewares) == 2
    
    def test_broker_with_rate_limiter_has_three_middlewares(self) -> None:
        """Broker has 3 middlewares when rate limiter enabled."""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            rate_limiter_enabled=True,
            rate_limiter_max_rate=100,
            rate_limiter_time_period=1.0,
        )
        registry = CollectorRegistry()
        
        broker = create_kafka_broker(
            settings,
            prometheus_registry=registry,
            enable_rate_limiter=True,
            rate_limit_max_rate=100,
            rate_limit_time_period=1.0,
        )
        
        # Circuit breaker + Rate limiter + Prometheus + (no Telemetry)
        assert len(broker.middlewares) == 3
    
    def test_rate_limiter_middleware_is_second_in_stack(self) -> None:
        """Rate limiter comes after circuit breaker in middleware stack."""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
        )
        
        broker = create_kafka_broker(
            settings,
            enable_rate_limiter=True,
            rate_limit_max_rate=50,
            rate_limit_time_period=2.0,
        )
        
        # middlewares[0] = circuit breaker factory
        # middlewares[1] = rate limiter instance
        assert len(broker.middlewares) >= 2
        rate_limiter = broker.middlewares[1]
        assert isinstance(rate_limiter, RateLimiterMiddleware)
        assert rate_limiter._limiter.max_rate == 50
        assert rate_limiter._limiter.time_period == 2.0
