"""Docker-gated Testcontainers smoke tests for eventing."""

from __future__ import annotations

import os

import pytest
from faststream.kafka import KafkaBroker
from testcontainers.kafka import KafkaContainer  # type: ignore[import-untyped]
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from eventing.core.contracts import BaseEvent, EventRegistry
from eventing.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from eventing.infrastructure.persistence.orm_base import Base
from eventing.infrastructure.persistence.session import create_session_factory


class ExampleEvent(BaseEvent):  # pylint: disable=too-many-ancestors
    """Concrete event used for container-backed smoke coverage."""

    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "user-123"
    source: str = "gamification-service"
    xp_delta: int


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
async def test_postgres_and_kafka_testcontainers_support_eventing_smoke(
    docker_or_skip: None,
) -> None:
    """A container-backed broker and database should support the core eventing smoke path."""
    del docker_or_skip
    postgres_password = os.getenv("TESTCONTAINERS_POSTGRES_PASSWORD", "postgres")
    kafka = KafkaContainer()
    with PostgresContainer(
        "postgres:16",
        username="postgres",
        password=postgres_password,
        dbname="eventing",
    ) as postgres:
        kafka.start(timeout=1800)
        engine, session_factory = create_session_factory(
            postgres.get_connection_url(driver="asyncpg")
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        broker = KafkaBroker(bootstrap_servers=kafka.get_bootstrap_server(), client_id="eventing-test")
        registry = EventRegistry()
        registry.register(ExampleEvent)
        repository = SqlAlchemyOutboxRepository(session_factory, registry)
        try:
            await broker.connect()
            await broker.start()
            await repository.add_event(ExampleEvent(xp_delta=15))
            pending = await repository.get_unpublished()
            assert len(pending) == 1
            assert await broker.ping(1.0) is True
        finally:
            await broker.stop()
            await engine.dispose()
            kafka.stop()
