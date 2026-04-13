"""Unit tests for initialization helpers with mocks.

Tests helper functions in _initialization.py using mocks to avoid
real infrastructure dependencies. Based on Serena MCP codebase analysis.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from faststream.confluent import KafkaBroker
from faststream.rabbit import RabbitBroker

from messaging.config import settings
from messaging.infrastructure.pubsub.bridge.config import BridgeConfig
from messaging.infrastructure.pubsub.rabbit.publisher import RabbitEventPublisher
from messaging.main._initialization import (
    attach_state_to_app,
    initialize_bridge_config,
    initialize_brokers_and_publishers,
    register_bridge_handler,
)


class TestInitializeBrokersAndPublishers:
    """Unit tests for initialize_brokers_and_publishers function."""

    @patch("messaging.infrastructure.pubsub.rabbit_broker_config.create_rabbit_broker")
    @patch("messaging.infrastructure.create_kafka_broker")
    def test_returns_correct_types(
        self, mock_create_kafka, mock_create_rabbit
    ) -> None:
        """Verify function returns correct types: KafkaBroker, RabbitBroker, Publisher."""
        # Setup mocks
        mock_kafka_broker = Mock(spec=KafkaBroker)
        mock_rabbit_broker = Mock(spec=RabbitBroker)
        mock_create_kafka.return_value = mock_kafka_broker
        mock_create_rabbit.return_value = mock_rabbit_broker

        # Execute
        broker, rabbit_broker, rabbit_publisher = initialize_brokers_and_publishers()

        # Verify
        assert broker is mock_kafka_broker
        assert rabbit_broker is mock_rabbit_broker
        assert isinstance(rabbit_publisher, RabbitEventPublisher)

    @patch("messaging.infrastructure.pubsub.rabbit_broker_config.create_rabbit_broker")
    @patch("messaging.infrastructure.create_kafka_broker")
    def test_passes_settings_to_kafka_broker(
        self, mock_create_rabbit, mock_create_kafka
    ) -> None:
        """Verify Kafka broker creation receives correct settings."""
        mock_kafka_broker = Mock(spec=KafkaBroker)
        mock_rabbit_broker = Mock(spec=RabbitBroker)
        mock_create_kafka.return_value = mock_kafka_broker
        mock_create_rabbit.return_value = mock_rabbit_broker

        initialize_brokers_and_publishers()

        # Verify create_kafka_broker called with settings
        mock_create_kafka.assert_called_once()
        call_args = mock_create_kafka.call_args
        assert call_args[0][0] is settings  # First positional arg

    @patch("messaging.infrastructure.pubsub.rabbit_broker_config.create_rabbit_broker")
    @patch("messaging.infrastructure.create_kafka_broker")
    def test_passes_rate_limiter_settings(
        self, mock_create_rabbit, mock_create_kafka
    ) -> None:
        """Verify rate limiter settings passed to both brokers."""
        mock_kafka_broker = Mock(spec=KafkaBroker)
        mock_rabbit_broker = Mock(spec=RabbitBroker)
        mock_create_kafka.return_value = mock_kafka_broker
        mock_create_rabbit.return_value = mock_rabbit_broker

        initialize_brokers_and_publishers()

        # Verify Kafka rate limiter kwargs
        kafka_kwargs = mock_create_kafka.call_args.kwargs
        assert "enable_rate_limiter" in kafka_kwargs
        assert "rate_limit_max_rate" in kafka_kwargs
        assert "rate_limit_time_period" in kafka_kwargs

        # Verify RabbitMQ rate limiter kwargs
        rabbit_kwargs = mock_create_rabbit.call_args.kwargs
        assert "enable_rate_limiter" in rabbit_kwargs
        assert "rate_limit_max_rate" in rabbit_kwargs
        assert "rate_limit_time_period" in rabbit_kwargs

    @patch("messaging.infrastructure.pubsub.rabbit_broker_config.create_rabbit_broker")
    @patch("messaging.infrastructure.create_kafka_broker")
    def test_rabbit_publisher_uses_correct_exchange(
        self, mock_create_rabbit, mock_create_kafka
    ) -> None:
        """Verify RabbitEventPublisher initialized with correct exchange."""
        mock_kafka_broker = Mock(spec=KafkaBroker)
        mock_rabbit_broker = Mock(spec=RabbitBroker)
        mock_create_kafka.return_value = mock_kafka_broker
        mock_create_rabbit.return_value = mock_rabbit_broker

        _, _, rabbit_publisher = initialize_brokers_and_publishers()

        # Verify publisher has correct broker and exchange
        assert rabbit_publisher._broker is mock_rabbit_broker
        # _default_exchange is a RabbitExchange object, check its name
        assert rabbit_publisher._default_exchange.name == settings.rabbitmq_exchange


class TestInitializeBridgeConfig:
    """Unit tests for initialize_bridge_config function."""

    def test_returns_bridge_config_instance(self) -> None:
        """Verify function returns BridgeConfig instance."""
        config = initialize_bridge_config()
        assert isinstance(config, BridgeConfig)

    def test_uses_correct_kafka_topic(self) -> None:
        """Verify config uses 'events' Kafka topic."""
        config = initialize_bridge_config()
        assert config.kafka_topic == "events"

    def test_uses_settings_rabbitmq_exchange(self) -> None:
        """Verify config uses exchange from settings."""
        config = initialize_bridge_config()
        assert config.rabbitmq_exchange == settings.rabbitmq_exchange

    def test_uses_correct_routing_key_template(self) -> None:
        """Verify routing key template extracts event_type."""
        config = initialize_bridge_config()
        assert config.routing_key_template == "{event_type}"


class TestRegisterBridgeHandler:
    """Unit tests for register_bridge_handler function.

    Based on Serena MCP analysis of BridgeConsumer interface:
    - __init__(rabbit_publisher, processed_message_store, routing_key_template)
    - handle_message(message) async method

    UPDATED: Handler now uses AckPolicy.MANUAL for bug fixes.
    """

    def test_registers_subscriber_on_kafka_broker(self) -> None:
        """Verify handler registered as subscriber with manual ack policy and group_id."""
        from faststream import AckPolicy

        mock_broker = Mock(spec=KafkaBroker)
        mock_config = Mock(spec=BridgeConfig)
        mock_config.kafka_topic = "test-events"
        mock_publisher = Mock(spec=RabbitEventPublisher)
        mock_session_factory = Mock()

        # Register handler
        register_bridge_handler(
            mock_broker, mock_config, mock_publisher, mock_session_factory
        )

        # Verify subscriber decorator called with manual ack policy and group_id
        mock_broker.subscriber.assert_called_once_with(
            "test-events", ack_policy=AckPolicy.MANUAL, group_id="eventing-consumers"
        )

    def test_handler_function_created(self) -> None:
        """Verify handle_kafka_event function is created."""

        mock_broker = Mock(spec=KafkaBroker)
        mock_config = Mock(spec=BridgeConfig)
        mock_config.kafka_topic = "events"
        mock_publisher = Mock()
        mock_session_factory = Mock()

        # Capture the decorated function
        registered_func = None

        def capture_subscriber(topic, _ack_policy=None, group_id=None):
            def decorator(func):
                nonlocal registered_func
                registered_func = func
                return func

            return decorator

        mock_broker.subscriber = capture_subscriber

        register_bridge_handler(
            mock_broker, mock_config, mock_publisher, mock_session_factory
        )

        # Verify function exists
        assert registered_func is not None
        assert registered_func.__name__ == "handle_kafka_event"

    @pytest.mark.asyncio
    async def test_handler_uses_session_factory(self) -> None:
        """Verify handler creates session from factory."""

        mock_broker = Mock(spec=KafkaBroker)
        mock_config = Mock(spec=BridgeConfig)
        mock_config.kafka_topic = "events"
        mock_config.routing_key_template = "{event_type}"
        mock_publisher = Mock()

        # Create mock session
        mock_session = AsyncMock()
        mock_session.begin = AsyncMock()
        mock_session.begin.return_value.__aenter__ = AsyncMock()
        mock_session.begin.return_value.__aexit__ = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_session_factory = Mock(return_value=mock_session)

        # Create mock KafkaMessage with ack method
        mock_kafka_msg = AsyncMock()
        mock_kafka_msg.ack = AsyncMock()

        # Capture handler
        registered_func = None

        def capture_subscriber(topic, _ack_policy=None, group_id=None):
            def decorator(func):
                nonlocal registered_func
                registered_func = func
                return func

            return decorator

        mock_broker.subscriber = capture_subscriber

        register_bridge_handler(
            mock_broker, mock_config, mock_publisher, mock_session_factory
        )

        # Execute handler with both message and msg parameters
        test_message = {"event_id": "test-1", "event_type": "user.created"}
        await registered_func(test_message, mock_kafka_msg)

        # Verify session factory was called
        mock_session_factory.assert_called_once()
        # Verify message was acked
        mock_kafka_msg.ack.assert_called_once()


class TestAttachStateToApp:
    """Unit tests for attach_state_to_app function."""

    def test_attaches_all_required_state(self) -> None:
        """Verify all infrastructure attached to FastAPI app.state."""
        from fastapi import FastAPI

        app = FastAPI()
        mock_broker = Mock(spec=KafkaBroker)
        mock_rabbit_broker = Mock(spec=RabbitBroker)
        mock_rabbit_publisher = Mock(spec=RabbitEventPublisher)
        mock_repository = Mock()

        attach_state_to_app(
            app,
            mock_broker,
            mock_rabbit_broker,
            mock_rabbit_publisher,
            mock_repository,
        )

        # Verify all state attributes exist
        assert hasattr(app.state, "broker")
        assert hasattr(app.state, "rabbit_broker")
        assert hasattr(app.state, "rabbit_publisher")
        assert hasattr(app.state, "outbox_health_check")
        assert hasattr(app.state, "outbox_repository")
        assert hasattr(app.state, "event_bus")

    def test_state_references_correct_instances(self) -> None:
        """Verify app.state contains correct object references."""
        from fastapi import FastAPI

        app = FastAPI()
        mock_broker = Mock(spec=KafkaBroker)
        mock_rabbit_broker = Mock(spec=RabbitBroker)
        mock_rabbit_publisher = Mock(spec=RabbitEventPublisher)
        mock_repository = Mock()

        attach_state_to_app(
            app,
            mock_broker,
            mock_rabbit_broker,
            mock_rabbit_publisher,
            mock_repository,
        )

        # Verify correct references
        assert app.state.broker is mock_broker
        assert app.state.rabbit_broker is mock_rabbit_broker
        assert app.state.rabbit_publisher is mock_rabbit_publisher
        assert app.state.outbox_repository is mock_repository

    def test_event_bus_created_with_empty_handlers(self) -> None:
        """Verify EventBus initialized with no handlers."""
        from fastapi import FastAPI

        app = FastAPI()
        mock_broker = Mock()
        mock_rabbit_broker = Mock()
        mock_rabbit_publisher = Mock()
        mock_repository = Mock()

        attach_state_to_app(
            app,
            mock_broker,
            mock_rabbit_broker,
            mock_rabbit_publisher,
            mock_repository,
        )

        # EventBus should exist (build_event_bus called with empty list)
        assert app.state.event_bus is not None
