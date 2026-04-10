"""Unit tests for rate limiter FastStream middleware."""

import asyncio
from typing import Any

import pytest
from faststream import StreamMessage

from messaging.infrastructure.resilience.rate_limiter_middleware import RateLimiterMiddleware


class TestRateLimiterMiddleware:
    """Test FastStream middleware integration for rate limiting."""

    @pytest.mark.asyncio
    async def test_middleware_gates_consume_scope(self) -> None:
        """Middleware wraps call_next with aiolimiter context manager."""
        middleware = RateLimiterMiddleware(max_rate=5, time_period=1.0)
        call_count = 0

        async def call_next(msg: StreamMessage[Any]) -> str:
            nonlocal call_count
            call_count += 1
            return "processed"

        msg = StreamMessage(raw_message=b"test", body={"test": "data"})
        result = await middleware.consume_scope(call_next, msg)

        assert result == "processed"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_middleware_blocks_over_rate_kafka(self) -> None:
        """Kafka rate limiter blocks N+1th message."""
        middleware = RateLimiterMiddleware(max_rate=2, time_period=0.2)
        processed: list[int] = []

        async def call_next(msg: StreamMessage[dict[str, Any]]) -> None:
            processed.append(msg.body["seq"])  # type: ignore[call-overload] # body dict access at runtime

        messages = [
            StreamMessage(raw_message=b"1", body={"seq": 1}),
            StreamMessage(raw_message=b"2", body={"seq": 2}),
            StreamMessage(raw_message=b"3", body={"seq": 3}),
        ]

        await asyncio.gather(*[
            middleware.consume_scope(call_next, msg)
            for msg in messages
        ])

        assert len(processed) == 3

    @pytest.mark.asyncio
    async def test_middleware_blocks_over_rate_rabbitmq(self) -> None:
        """RabbitMQ rate limiter blocks N+1th message."""
        middleware = RateLimiterMiddleware(max_rate=2, time_period=0.2)
        processed: list[int] = []

        async def call_next(msg: StreamMessage[dict[str, Any]]) -> None:
            processed.append(msg.body["seq"])  # type: ignore[call-overload] # body dict access at runtime

        messages = [
            StreamMessage(raw_message=b"1", body={"seq": 1}),
            StreamMessage(raw_message=b"2", body={"seq": 2}),
            StreamMessage(raw_message=b"3", body={"seq": 3}),
        ]

        await asyncio.gather(*[
            middleware.consume_scope(call_next, msg)
            for msg in messages
        ])

        assert len(processed) == 3
