"""HTTP client fixtures for API testing."""

import asyncio
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


@pytest.fixture
async def async_client(
    skip_broker_in_tests: None,
    sqlite_session_factory: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> AsyncIterator[AsyncClient]:
    """Create async HTTP client for HTTP-only tests (no external brokers)."""
    from messaging.main import create_app

    app = create_app()

    engine, session_factory = sqlite_session_factory
    app.state.session_factory = session_factory

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
async def async_client_with_kafka(
    kafka_container,
    rabbitmq_container,
    sqlite_session_factory: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    """Create async HTTP client with real Kafka and RabbitMQ for integration tests."""
    from messaging.main import create_app

    kafka_bootstrap = kafka_container.get_bootstrap_server()
    rabbitmq_url = (
        f"amqp://{rabbitmq_container.username}:{rabbitmq_container.password}"
        f"@{rabbitmq_container.get_container_host_ip()}"
        f":{rabbitmq_container.get_exposed_port(rabbitmq_container.port)}//"
    )

    from messaging.config import settings as app_settings

    monkeypatch.setattr(app_settings, "kafka_bootstrap_servers", kafka_bootstrap)
    monkeypatch.setattr(app_settings, "rabbitmq_url", rabbitmq_url)

    app = create_app()

    engine, session_factory = sqlite_session_factory
    app.state.session_factory = session_factory

    import aio_pika

    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()
    await channel.declare_exchange("events", type=aio_pika.ExchangeType.TOPIC, durable=True)
    await connection.close()

    async with app.router.lifespan_context(app) as state:
        if state:
            app.state._state.update(state)

        await asyncio.sleep(5)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
