"""Unit tests for circuit breaker state machine."""

import asyncio

import pytest

from messaging.core.contracts.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


class TestCircuitBreakerStateMachine:
    """Test circuit breaker CLOSED->OPEN->HALF_OPEN->CLOSED transitions."""

    @pytest.mark.asyncio
    async def test_default_state_is_closed(self) -> None:
        """Circuit starts in CLOSED state, all calls pass through."""
        breaker = CircuitBreaker(failure_threshold=3)

        async def success_func() -> str:
            return "ok"

        result = await breaker.call(success_func)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self) -> None:
        """Circuit opens after N consecutive failures."""
        breaker = CircuitBreaker(failure_threshold=3)

        async def failing_func() -> None:
            msg = "Broker down"
            raise ValueError(msg)

        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self) -> None:
        """OPEN circuit raises CircuitOpenError without calling function."""
        breaker = CircuitBreaker(failure_threshold=2)
        call_count = 0

        async def failing_func() -> None:
            nonlocal call_count
            call_count += 1
            msg = "down"
            raise ValueError(msg)

        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        with pytest.raises(CircuitOpenError):
            await breaker.call(failing_func)

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_half_open_after_reset_timeout(self) -> None:
        """Circuit transitions to HALF_OPEN after reset_timeout."""
        breaker = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)

        async def failing_func() -> None:
            msg = "down"
            raise ValueError(msg)

        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        await asyncio.sleep(0.15)

        # State transitions to HALF_OPEN after reset_timeout (runtime state change)
        current_state = breaker.state
        assert current_state == CircuitState.HALF_OPEN  # type: ignore[comparison-overlap] # state property changes at runtime based on elapsed time

    @pytest.mark.asyncio
    async def test_half_open_successful_call_closes_circuit(self) -> None:
        """Successful call in HALF_OPEN transitions to CLOSED."""
        breaker = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)

        async def sometimes_works() -> str:
            return "recovered"

        async def always_fails() -> None:
            msg = "down"
            raise ValueError(msg)

        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(always_fails)

        await asyncio.sleep(0.15)

        result = await breaker.call(sometimes_works)
        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failed_call_reopens_circuit(self) -> None:
        """Failed call in HALF_OPEN transitions back to OPEN."""
        breaker = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)

        async def failing_func() -> None:
            msg = "still down"
            raise ValueError(msg)

        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        await asyncio.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        # Failed call transitions back to OPEN (runtime state change)
        current_state = breaker.state
        assert current_state == CircuitState.OPEN  # type: ignore[comparison-overlap] # state property changes at runtime after failed call

    @pytest.mark.asyncio
    async def test_half_open_rejects_concurrent_calls(self) -> None:
        """HALF_OPEN allows only one test call at a time."""
        breaker = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)

        async def failing_func() -> None:
            msg = "down"
            raise ValueError(msg)

        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        await asyncio.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        async def slow_recovery() -> str:
            await asyncio.sleep(0.2)
            return "ok"

        task1 = asyncio.create_task(breaker.call(slow_recovery))
        await asyncio.sleep(0.05)

        with pytest.raises(CircuitOpenError, match="half-open.*single test"):
            await breaker.call(slow_recovery)

        await task1
