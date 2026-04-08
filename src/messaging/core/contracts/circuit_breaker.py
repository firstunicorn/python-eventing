"""Async circuit breaker state machine for broker failures."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from enum import Enum
from typing import Any


class CircuitOpenError(Exception):
    """Raised when circuit is open and calls are rejected."""


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Async circuit breaker with closed/open/half-open states."""

    def __init__(self, failure_threshold: int, reset_timeout: float = 30.0) -> None:
        """Initialize circuit breaker."""
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time: float | None = None
        self._half_open_lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, transitioning to half-open if timeout elapsed."""
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            elapsed = asyncio.get_event_loop().time() - self._last_failure_time
            if elapsed >= self._reset_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            msg = "Circuit is open, rejecting call"
            raise CircuitOpenError(msg)

        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_lock.locked():
                msg = "Circuit is half-open, only single test call allowed"
                raise CircuitOpenError(msg)
            async with self._half_open_lock:
                return await self._execute_call(func, *args, **kwargs)

        return await self._execute_call(func, *args, **kwargs)

    async def _execute_call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function and handle result."""
        try:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            elif asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception:
            await self.record_failure()
            raise

    async def record_success(self) -> None:
        """Record successful call."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    async def record_failure(self) -> None:
        """Record failed call."""
        self._failure_count += 1
        self._last_failure_time = asyncio.get_event_loop().time()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
