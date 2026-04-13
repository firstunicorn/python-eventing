"""Setup helpers for testcontainers smoke test."""

import asyncio
import os

from testcontainers.kafka import KafkaContainer
from testcontainers.postgres import PostgresContainer

from messaging.config import Settings
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from messaging.infrastructure.persistence.orm_models.orm_base import Base
from messaging.infrastructure.persistence.session import create_session_factory
from messaging.infrastructure.pubsub import KafkaEventPublisher, create_kafka_broker


async def setup_containers_and_infrastructure(kafka: KafkaContainer, postgres: PostgresContainer):
    """Set up Kafka and Postgres containers with necessary infrastructure.

    Returns:
        Tuple of (engine, session_factory, broker, repository, publisher, bootstrap_servers)
    """
    kafka.start(timeout=300)

    engine, session_factory = create_session_factory(
        postgres.get_connection_url(driver="asyncpg")
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    bootstrap_servers = kafka.get_bootstrap_server()

    broker = create_kafka_broker(
        Settings(
            kafka_bootstrap_servers=bootstrap_servers,
            kafka_client_id="eventing-test",
        )
    )

    repository = SqlAlchemyOutboxRepository(session_factory)
    publisher = KafkaEventPublisher(broker)

    await broker.connect()
    await broker.start()

    await asyncio.sleep(5)

    return engine, session_factory, broker, repository, publisher, bootstrap_servers


def create_postgres_container() -> PostgresContainer:
    """Create and configure a Postgres testcontainer."""
    return PostgresContainer(
        "postgres:16",
        username="postgres",
        password=os.getenv("TESTCONTAINERS_POSTGRES_PASSWORD", "postgres"),
        dbname="eventing",
    )
