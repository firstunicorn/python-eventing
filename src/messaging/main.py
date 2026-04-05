"""FastAPI application entrypoint for the eventing service.

This module provides the `create_app` factory and application lifecycle
manager. It wires together the database session, Kafka broker, outbox repository,
and background worker, ensuring all infrastructure is properly initialized
and gracefully shut down.

See Also
--------
- messaging.presentation.router : API routes registered with the application
- messaging.config.Settings : Configuration used during initialization
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import APIRouter, FastAPI

from fastapi_middleware_toolkit import setup_cors_middleware, setup_error_handlers
from messaging.config import settings
from messaging.core.contracts import EventRegistry
from messaging.infrastructure import (
    DeadLetterHandler,
    EventingHealthCheck,
    KafkaEventPublisher,
    ScheduledOutboxWorker,
    SqlAlchemyOutboxRepository,
    build_outbox_config,
    create_kafka_broker,
    create_session_factory,
)
from messaging.presentation.router import api_router


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
    app.include_router(root_router)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down outbox infrastructure for the service."""
    engine, session_factory = create_session_factory(settings.database_url)
    registry = EventRegistry()
    broker = create_kafka_broker(settings)
    repository = SqlAlchemyOutboxRepository(session_factory, registry)
    publisher = KafkaEventPublisher(broker)
    worker = ScheduledOutboxWorker(
        repository=repository,
        publisher=publisher,
        config=build_outbox_config(settings),
        dead_letter_handler=DeadLetterHandler(repository, publisher),
    )
    app.state.session_factory = session_factory
    app.state.outbox_health_check = EventingHealthCheck(repository, broker)
    app.state.outbox_repository = repository
    task: asyncio.Task[None] | None = None
    try:
        if settings.outbox_worker_enabled:
            await broker.connect()
            await broker.start()
            task = asyncio.create_task(worker.schedule_publishing())
        yield
    finally:
        if task is not None:
            await worker.stop()
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await broker.close()
        await engine.dispose()


app = create_app()
