"""Unit tests for circuit breaker FastStream middleware."""

from typing import Any

import pytest
from faststream import PublishCommand, PublishType, StreamMessage

from messaging.core.contracts.circuit_breaker import CircuitOpenError, CircuitState
from messaging.infrastructure.resilience.circuit_breaker_middleware import CircuitBreakerMiddleware


class TestCircuitBreakerMiddleware:
    """Test FastStream middleware integration for circuit breaker."""

    @pytest.mark.asyncio
    async def test_middleware_wraps_consume_scope(self) -> None:
        """Middleware delegates to CircuitBreaker.call()."""
        middleware = CircuitBreakerMiddleware(failure_threshold=3)
        call_count = 0

        async def call_next(msg: StreamMessage[Any]) -> str:
            nonlocal call_count
            call_count += 1
            return "processed"

        msg = StreamMessage(raw_message=b"test", body={"test": "data"})
        result = await middleware.consume_scope(call_next, msg)

        assert result == "processed"
        assert call_count == 1
        assert middleware._breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_middleware_records_failure_and_opens_circuit(self) -> None:
        """Middleware records failures, circuit opens after threshold."""
        middleware = CircuitBreakerMiddleware(failure_threshold=2)

        async def failing_call_next(msg: StreamMessage[Any]) -> None:
            msg = "Kafka connection failed"
            raise ValueError(msg)

        msg = StreamMessage(raw_message=b"test", body={"test": "data"})

        for _ in range(2):
            with pytest.raises(ValueError):
                await middleware.consume_scope(failing_call_next, msg)

        assert middleware._breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_raises_before_call_next(self) -> None:
        """OPEN circuit raises CircuitOpenError without calling call_next."""
        middleware = CircuitBreakerMiddleware(failure_threshold=2)
        call_count = 0

        async def failing_call_next(msg: StreamMessage[Any]) -> None:
            nonlocal call_count
            call_count += 1
            msg = "down"
            raise ValueError(msg)

        msg = StreamMessage(raw_message=b"test", body={"test": "data"})

        for _ in range(2):
            with pytest.raises(ValueError):
                await middleware.consume_scope(failing_call_next, msg)

        assert middleware._breaker.state == CircuitState.OPEN
        assert call_count == 2

        with pytest.raises(CircuitOpenError):
            await middleware.consume_scope(failing_call_next, msg)

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_middleware_wraps_publish_scope(self) -> None:
        """Middleware wraps publish operations with circuit breaker."""
        middleware = CircuitBreakerMiddleware(failure_threshold=3)
        call_count = 0

        async def call_next(cmd: PublishCommand) -> None:
            nonlocal call_count
            call_count += 1

        cmd = PublishCommand(
            {"test": "data"},
            _publish_type=PublishType.PUBLISH,
            destination="test-topic",
        )
        await middleware.publish_scope(call_next, cmd)

        assert call_count == 1
        assert middleware._breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_publish_scope_opens_circuit_on_failures(self) -> None:
        """Publish scope records failures and opens circuit."""
        middleware = CircuitBreakerMiddleware(failure_threshold=2)

        async def failing_publish(cmd: PublishCommand) -> None:
            msg = "Kafka broker down"
            raise ConnectionError(msg)

        cmd = PublishCommand(
            {"test": "data"},
            _publish_type=PublishType.PUBLISH,
            destination="test-topic",
        )

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await middleware.publish_scope(failing_publish, cmd)

        assert middleware._breaker.state == CircuitState.OPEN

        # Next publish should raise CircuitOpenError immediately
        with pytest.raises(CircuitOpenError):
            await middleware.publish_scope(failing_publish, cmd)
