"""FastAPI application entrypoint for the eventing service.

This module provides the `create_app` factory and application lifecycle
manager. It wires together the database session, Kafka broker, and outbox repository.
Outbox publishing is delegated to Kafka Connect (Debezium).

See Also
--------
- messaging.presentation.router : API routes registered with the application
- messaging.config.Settings : Configuration used during initialization
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from fastapi_middleware_toolkit import setup_cors_middleware, setup_error_handlers
from messaging.config import settings
from messaging.core.contracts import build_event_bus
from messaging.infrastructure import (
    EventingHealthCheck,
    SqlAlchemyOutboxRepository,
    create_kafka_broker,
    create_session_factory,
)
from messaging.presentation.router import api_router
from messaging.presentation.dlq_routes import router as dlq_router
from messaging.presentation.replay_routes import router as replay_router


def create_app() -> FastAPI:
    """Create the FastAPI app instance."""
    app = FastAPI(
        title=settings.service_name,
        debug=settings.debug,
        lifespan=lifespan,
    )
    setup_cors_middleware(
        app,
        settings.allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        max_age=settings.cors_max_age,
    )
    setup_error_handlers(app)
    root_router = APIRouter(prefix=settings.api_prefix)
    root_router.include_router(api_router)
    root_router.include_router(dlq_router)
    root_router.include_router(replay_router)
    app.include_router(root_router)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down infrastructure for the service.

    This lifespan manager wires up the complete event infrastructure:
    1. Database session factory for persistence
    2. EventBus for domain event dispatch (handlers registered per-route as needed)
    3. Kafka broker for external messaging

    Outbox publishing is handled by Kafka Connect (Debezium CDC).

    The EventBus enables decoupled domain event dispatch within the service.
    Handlers can register for specific event types using:
        app.state.session_factory = session_factory
        @app.state.event_bus.subscriber(EventType)
        async def handle_event(event: EventType): ...

    Args:
        app: FastAPI application instance

    Yields:
        None: Control flow during application runtime
    """
    import os

    # Use pre-set test session factory if available (for testing)
    if hasattr(app.state, "session_factory"):
        session_factory = app.state.session_factory
        engine = None  # Test fixture manages engine lifecycle
    else:
        engine, session_factory = create_session_factory(settings.database_url)
        app.state.session_factory = session_factory

    broker = create_kafka_broker(
        settings,
        enable_rate_limiter=settings.rate_limiter_enabled,
        rate_limit_max_rate=settings.rate_limiter_max_rate,
        rate_limit_time_period=settings.rate_limiter_time_period,
    )
    repository = SqlAlchemyOutboxRepository(session_factory)

    # Initialize EventBus (handlers registered per-domain as needed)
    event_bus = build_event_bus([])

    app.state.broker = broker
    app.state.outbox_health_check = EventingHealthCheck(repository, broker)
    app.state.outbox_repository = repository
    app.state.event_bus = event_bus  # Expose EventBus for API handlers

    skip_broker = os.getenv("TESTING_SKIP_BROKER") == "true"

    try:
        if not skip_broker:
            await broker.connect()
            await broker.start()
        yield
    finally:
        if not skip_broker:
            await broker.close()
        if engine is not None:
            await engine.dispose()


app = create_app()
