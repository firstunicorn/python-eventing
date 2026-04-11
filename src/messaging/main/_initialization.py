"""Initialization helpers for application infrastructure."""

from typing import Any

from fastapi import FastAPI
from faststream.confluent import KafkaBroker
from faststream.rabbit import RabbitBroker

from messaging.config import settings
from messaging.core.contracts import build_event_bus
from messaging.infrastructure import (
    EventingHealthCheck,
    SqlAlchemyOutboxRepository,
    SqlAlchemyProcessedMessageStore,
    create_kafka_broker,
)
from messaging.infrastructure.pubsub.bridge.config import BridgeConfig
from messaging.infrastructure.pubsub.bridge.consumer import BridgeConsumer
from messaging.infrastructure.pubsub.rabbit.publisher import RabbitEventPublisher
from messaging.infrastructure.pubsub.rabbit_broker_config import create_rabbit_broker


def initialize_brokers_and_publishers() -> (
    tuple[
        KafkaBroker,
        RabbitBroker,
        RabbitEventPublisher,
    ]
):
    """Initialize Kafka and RabbitMQ brokers with publishers.

    Returns:
        Tuple of (kafka_broker, rabbit_broker, rabbit_publisher)
    """
    broker = create_kafka_broker(
        settings,
        enable_rate_limiter=settings.rate_limiter_enabled,
        rate_limit_max_rate=settings.rate_limiter_max_rate,
        rate_limit_time_period=settings.rate_limiter_time_period,
    )

    rabbit_broker = create_rabbit_broker(
        settings,
        enable_rate_limiter=settings.rabbitmq_rate_limiter_enabled,
        rate_limit_max_rate=settings.rabbitmq_rate_limit,
        rate_limit_time_period=settings.rabbitmq_rate_interval,
    )

    rabbit_publisher = RabbitEventPublisher(
        broker=rabbit_broker,
        default_exchange=settings.rabbitmq_exchange,
    )

    return broker, rabbit_broker, rabbit_publisher


def initialize_bridge_config() -> BridgeConfig:
    """Initialize Kafka-to-RabbitMQ bridge configuration.

    Returns:
        BridgeConfig: Bridge configuration
    """
    return BridgeConfig(
        kafka_topic="events",
        rabbitmq_exchange=settings.rabbitmq_exchange,
        routing_key_template="{event_type}",
    )


def register_bridge_handler(
    broker: KafkaBroker,
    bridge_config: BridgeConfig,
    rabbit_publisher: RabbitEventPublisher,
    session_factory: Any,
) -> None:
    """Register bridge consumer as Kafka subscriber.

    Args:
        broker: Kafka broker
        bridge_config: Bridge configuration
        rabbit_publisher: RabbitMQ publisher
        session_factory: SQLAlchemy async session factory
    """

    # CRITICAL BUG FIX: Per-message session and transaction scope
    # BUG HISTORY: SqlAlchemyProcessedMessageStore singleton initialized with async_sessionmaker
    #              instead of AsyncSession → AttributeError: no 'in_transaction'.
    #              Idempotency checks completely broken.
    # SOLUTION: Instantiate store+consumer per message within session context.
    # WHY session.begin(): INSERT...ON CONFLICT + RabbitMQ publish must be atomic.
    #                      Without begin(), autocommit claims message even if publish fails.
    # WHY combined `with`: Ruff SIM117 requires combining nested async context managers.

    @broker.subscriber(bridge_config.kafka_topic)
    async def handle_kafka_event(message: dict[str, Any]) -> None:
        """Bridge handler: consume from Kafka, forward to RabbitMQ.

        Args:
            message: Kafka message dict containing event_id and event_type
        """
        async with session_factory() as session, session.begin():
            # Create fresh store and consumer for THIS message only
            # Store wraps the active session (not the factory)
            store = SqlAlchemyProcessedMessageStore(session)
            consumer = BridgeConsumer(
                rabbit_publisher=rabbit_publisher,
                processed_message_store=store,
                routing_key_template=bridge_config.routing_key_template,
            )
            # handle_message() performs: claim → publish
            # Commit happens automatically via `begin()` context manager
            await consumer.handle_message(message)


def attach_state_to_app(
    app: FastAPI,
    broker: KafkaBroker,
    rabbit_broker: RabbitBroker,
    rabbit_publisher: RabbitEventPublisher,
    repository: SqlAlchemyOutboxRepository,
) -> None:
    """Attach all infrastructure instances to FastAPI app state.

    Args:
        app: FastAPI application
        broker: Kafka broker
        rabbit_broker: RabbitMQ broker
        rabbit_publisher: RabbitMQ publisher
        repository: Outbox repository
    """
    event_bus = build_event_bus([])

    app.state.broker = broker
    app.state.rabbit_broker = rabbit_broker
    app.state.rabbit_publisher = rabbit_publisher
    app.state.outbox_health_check = EventingHealthCheck(repository, broker)
    app.state.outbox_repository = repository
    app.state.event_bus = event_bus
