"""Circuit breaker factory helpers for RabbitMQ broker."""

from collections.abc import Callable
from typing import Any

from messaging.core.contracts.circuit_breaker import CircuitBreaker
from messaging.infrastructure.resilience.circuit_breaker_middleware import CircuitBreakerMiddleware


def create_circuit_breaker_factory(
    shared_breaker: CircuitBreaker,
    circuit_breaker_threshold: int,
    circuit_breaker_timeout: float,
) -> Callable[[Any, Any], CircuitBreakerMiddleware]:
    """Create circuit breaker factory for FastStream middleware.

    FastStream requires a factory function that accepts (msg, context) and returns middleware.

    Args:
        shared_breaker: Shared circuit breaker instance.
        circuit_breaker_threshold: Number of failures before circuit opens.
        circuit_breaker_timeout: Seconds before half-open state.

    Returns:
        Factory function that creates CircuitBreakerMiddleware with shared breaker.
    """

    # LINTER EXCLUSION: ARG001 suppressed for msg and context parameters
    # RATIONALE: FastStream middleware factory REQUIRES (msg, context) signature.
    #            Cannot remove even though unused (framework interface requirement).
    def circuit_breaker_factory(
        msg: Any = None,  # noqa: ARG001
        context: Any = None,  # noqa: ARG001
    ) -> CircuitBreakerMiddleware:
        # Parameters required by FastStream middleware interface but unused
        # shared_breaker from closure used instead of per-message state
        middleware = CircuitBreakerMiddleware(
            failure_threshold=circuit_breaker_threshold,
            reset_timeout=circuit_breaker_timeout,
        )
        middleware._breaker = shared_breaker
        return middleware

    return circuit_breaker_factory
