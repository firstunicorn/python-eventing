"""FastStream contract tests using inspect.signature().

Validates that our middleware implementations match FastStream's expected signatures.
Ensures compatibility with FastStream's BaseMiddleware interface.
"""

import inspect

from faststream import BaseMiddleware

from messaging.infrastructure.pubsub.broker_config._factory_helpers import (
    create_circuit_breaker_factory,
)
from messaging.infrastructure.resilience.circuit_breaker_middleware import CircuitBreakerMiddleware
from messaging.infrastructure.resilience.rate_limiter_middleware import RateLimiterMiddleware


def test_middleware_factory_returns_correct_signature() -> None:
    """Verify create_circuit_breaker_factory returns Callable[[Any, Any], Middleware].

    FastStream requires middleware factories with exact (msg, context) signature.
    """
    from messaging.core.contracts.circuit_breaker import CircuitBreaker

    shared_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=60.0)
    factory = create_circuit_breaker_factory(
        shared_breaker=shared_breaker,
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=60.0,
    )

    # Verify factory is callable
    assert callable(factory)

    # Verify factory signature: (msg, context) -> Middleware
    sig = inspect.signature(factory)
    params = list(sig.parameters.keys())
    assert len(params) == 2
    assert params[0] == "msg"
    assert params[1] == "context"

    # Verify factory returns CircuitBreakerMiddleware
    middleware = factory(None, None)
    assert isinstance(middleware, CircuitBreakerMiddleware)


def test_consume_scope_signature_matches_base_middleware() -> None:
    """Verify consume_scope signature matches FastStream.BaseMiddleware."""
    # Get FastStream's BaseMiddleware.consume_scope signature
    base_sig = inspect.signature(BaseMiddleware.consume_scope)
    base_params = list(base_sig.parameters.keys())

    # Verify CircuitBreakerMiddleware.consume_scope
    circuit_sig = inspect.signature(CircuitBreakerMiddleware.consume_scope)
    circuit_params = list(circuit_sig.parameters.keys())

    assert circuit_params == base_params
    assert "self" in circuit_params
    assert "call_next" in circuit_params
    assert "msg" in circuit_params

    # Verify RateLimiterMiddleware.consume_scope
    limiter_sig = inspect.signature(RateLimiterMiddleware.consume_scope)
    limiter_params = list(limiter_sig.parameters.keys())

    assert limiter_params == base_params


def test_publish_scope_signature_matches_base_middleware() -> None:
    """Verify publish_scope signature matches FastStream.BaseMiddleware."""
    base_sig = inspect.signature(BaseMiddleware.publish_scope)
    base_params = list(base_sig.parameters.keys())

    circuit_sig = inspect.signature(CircuitBreakerMiddleware.publish_scope)
    circuit_params = list(circuit_sig.parameters.keys())

    assert circuit_params == base_params
    assert "self" in circuit_params
    assert "call_next" in circuit_params
    assert "cmd" in circuit_params


def test_after_processed_signature_matches_base_middleware() -> None:
    """Verify after_processed signature matches FastStream.BaseMiddleware."""
    base_sig = inspect.signature(BaseMiddleware.after_processed)
    base_params = list(base_sig.parameters.keys())

    # BaseMiddleware defines after_processed with exc_type, exc_val, exc_tb
    assert "self" in base_params
    assert "exc_type" in base_params
    assert "exc_val" in base_params
    assert "exc_tb" in base_params
