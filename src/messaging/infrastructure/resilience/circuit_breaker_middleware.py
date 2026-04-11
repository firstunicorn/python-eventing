"""FastStream middleware for circuit breaker."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from faststream import BaseMiddleware, PublishCommand, StreamMessage

from messaging.core.contracts.circuit_breaker import CircuitBreaker


class CircuitBreakerMiddleware(BaseMiddleware):
    """FastStream middleware wrapping CircuitBreaker for both consume and publish."""

    def __init__(self, failure_threshold: int, reset_timeout: float = 30.0) -> None:
        """Initialize middleware with circuit breaker."""
        self._breaker = CircuitBreaker(failure_threshold, reset_timeout)

    async def consume_scope(self, call_next: Any, msg: StreamMessage[Any]) -> Any:
        """Wrap consume with circuit breaker."""
        return await self._breaker.call(call_next, msg)

    async def publish_scope(
        self,
        call_next: Callable[[PublishCommand], Awaitable[Any]],
        cmd: PublishCommand,
    ) -> Any:
        """Wrap publish with circuit breaker."""
        return await self._breaker.call(call_next, cmd)
