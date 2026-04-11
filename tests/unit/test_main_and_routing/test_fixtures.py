"""Shared test fixtures for main and routing tests."""

from __future__ import annotations


class DummyChecker:
    """Health checker fake for route coverage."""

    async def check_health(self) -> dict[str, object]:
        return {"status": "healthy", "checks": {"database": {"status": "healthy"}}}


class FakeBroker:
    """Broker fake that records lifecycle operations."""

    def __init__(self) -> None:
        self.connected = False
        self.started = False
        self.closed = False

    async def connect(self) -> None:
        self.connected = True

    async def start(self) -> None:
        self.started = True

    async def close(self) -> None:
        """Deprecated method kept for backwards compatibility."""
        self.closed = True

    async def stop(self) -> None:
        """Modern method for stopping the broker."""
        self.closed = True

    def subscriber(self, topic: str):
        """Mock subscriber decorator that returns the decorated function unchanged."""

        def decorator(func):
            return func

        return decorator


class FakeEngine:
    """Engine fake used to verify disposal."""

    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True
