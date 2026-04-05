"""Tests for app wiring, routing helpers, and lifespan behavior."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute

from messaging.infrastructure.outbox import build_outbox_config
from messaging.infrastructure.persistence.session import create_session_factory
from messaging.main import create_app, lifespan
from messaging.presentation.router import outbox_health


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
        self.closed = True


class FakeEngine:
    """Engine fake used to verify disposal."""

    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


class FakeWorker:
    """Worker fake that can be scheduled and stopped."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.stop_called = False

    async def schedule_publishing(self) -> None:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            raise

    async def stop(self) -> None:
        self.stop_called = True


@pytest.mark.asyncio
async def test_outbox_health_returns_unavailable_without_checker() -> None:
    """Route should raise 503 when lifespan has not set a checker."""
    from fastapi import HTTPException

    from messaging.presentation.dependencies import get_outbox_health_check

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    with pytest.raises(HTTPException) as exc_info:
        await get_outbox_health_check(request)  # type: ignore[arg-type]

    assert exc_info.value.status_code == 503
    assert "not initialized" in exc_info.value.detail


@pytest.mark.asyncio
async def test_outbox_health_uses_checker_when_present() -> None:
    """Route should delegate to the configured checker."""

    result = await outbox_health(checker=DummyChecker())  # type: ignore[call-arg]

    assert result["status"] == "healthy"


def test_build_outbox_config_maps_settings_values() -> None:
    """Settings should map directly into the outbox core config object."""
    settings = SimpleNamespace(
        outbox_batch_size=10,
        outbox_poll_interval_seconds=7,
        outbox_max_retry_count=4,
        outbox_retry_backoff_multiplier=3.0,
    )

    config = build_outbox_config(settings)  # type: ignore[arg-type]

    assert config.batch_size == 10
    assert config.poll_interval_seconds == 7
    assert config.max_retry_count == 4
    assert config.retry_backoff_multiplier == 3.0


@pytest.mark.asyncio
async def test_create_session_factory_creates_async_engine() -> None:
    """Session helper should return an engine and a session factory."""
    engine, factory = create_session_factory(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/eventing"
    )

    assert factory.kw["expire_on_commit"] is False
    await engine.dispose()


def test_create_app_sets_title_and_registers_routes() -> None:
    """App factory should keep service metadata and include health routes."""
    app = create_app()
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}

    assert app.title == "eventing"
    assert "/api/v1/health" in paths
    assert "/api/v1/health/outbox" in paths


@pytest.mark.asyncio
async def test_lifespan_initializes_state_without_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifespan should initialize infrastructure state even when worker is disabled."""
    engine = FakeEngine()
    broker = FakeBroker()
    monkeypatch.setattr(
        "messaging.main.settings", SimpleNamespace(database_url="db", outbox_worker_enabled=False)
    )
    monkeypatch.setattr("messaging.main.create_session_factory", lambda _: (engine, object()))
    monkeypatch.setattr("messaging.main.EventRegistry", lambda: object())
    monkeypatch.setattr("messaging.main.create_kafka_broker", lambda _: broker)
    monkeypatch.setattr(
        "messaging.main.SqlAlchemyOutboxRepository", lambda session_factory, registry: "repo"
    )
    monkeypatch.setattr("messaging.main.KafkaEventPublisher", lambda broker: "publisher")
    monkeypatch.setattr("messaging.main.build_outbox_config", lambda _: "config")
    monkeypatch.setattr("messaging.main.DeadLetterHandler", lambda repository, publisher: "dlq")
    monkeypatch.setattr("messaging.main.ScheduledOutboxWorker", lambda **kwargs: FakeWorker())
    monkeypatch.setattr("messaging.main.EventingHealthCheck", lambda repository, broker: "health")
    app = FastAPI()

    async with lifespan(app):
        assert app.state.outbox_repository == "repo"
        assert app.state.outbox_health_check == "health"
        assert broker.connected is False

    assert engine.disposed is True


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_worker_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lifespan should start broker/worker and close them on shutdown."""
    engine = FakeEngine()
    broker = FakeBroker()
    worker = FakeWorker()
    monkeypatch.setattr(
        "messaging.main.settings", SimpleNamespace(database_url="db", outbox_worker_enabled=True)
    )
    monkeypatch.setattr("messaging.main.create_session_factory", lambda _: (engine, object()))
    monkeypatch.setattr("messaging.main.EventRegistry", lambda: object())
    monkeypatch.setattr("messaging.main.create_kafka_broker", lambda _: broker)
    monkeypatch.setattr(
        "messaging.main.SqlAlchemyOutboxRepository", lambda session_factory, registry: "repo"
    )
    monkeypatch.setattr("messaging.main.KafkaEventPublisher", lambda broker: "publisher")
    monkeypatch.setattr("messaging.main.build_outbox_config", lambda _: "config")
    monkeypatch.setattr("messaging.main.DeadLetterHandler", lambda repository, publisher: "dlq")
    monkeypatch.setattr("messaging.main.ScheduledOutboxWorker", lambda **kwargs: worker)
    monkeypatch.setattr("messaging.main.EventingHealthCheck", lambda repository, broker: "health")
    app = FastAPI()

    async with lifespan(app):
        assert broker.connected is True
        assert broker.started is True

    assert worker.stop_called is True
    assert broker.closed is True
    assert engine.disposed is True
