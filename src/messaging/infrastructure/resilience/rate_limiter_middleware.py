"""FastStream middleware for rate limiting via aiolimiter."""

from __future__ import annotations

from typing import Any

from aiolimiter import AsyncLimiter
from faststream import BaseMiddleware, StreamMessage


class RateLimiterMiddleware(BaseMiddleware):
    """FastStream middleware for rate limiting via aiolimiter."""

    def __init__(self, max_rate: int, time_period: float = 1.0) -> None:
        """Initialize middleware with rate limiter."""
        self._limiter = AsyncLimiter(max_rate, time_period)

    async def consume_scope(self, call_next: Any, msg: StreamMessage[Any]) -> Any:
        """Gate message consumption with rate limiter."""
        async with self._limiter:
            return await call_next(msg)
