"""Setup helpers for bridge handler integration tests."""

from typing import Any

from messaging.config import settings as app_settings
from messaging.main._initialization import (
    initialize_brokers_and_publishers,
    register_bridge_handler,
)


def setup_test_containers_config(
    kafka_container: Any,
    rabbitmq_container: Any,
    monkeypatch: Any,
    exchange: str = "test-events",
    consumer_group_id: str = "eventing-consumers",
    kafka_topic: str = "events",
) -> tuple[str, str, str]:
    """Configure app settings to use test containers."""
    kafka_bootstrap = kafka_container.get_bootstrap_server()
    rabbitmq_url = (
        f"amqp://{rabbitmq_container.username}:{rabbitmq_container.password}"
        f"@{rabbitmq_container.get_container_host_ip()}"
        f":{rabbitmq_container.get_exposed_port(rabbitmq_container.port)}//"
    )

    monkeypatch.setattr(app_settings, "kafka_bootstrap_servers", kafka_bootstrap)
    monkeypatch.setattr(app_settings, "rabbitmq_url", rabbitmq_url)
    monkeypatch.setattr(app_settings, "rabbitmq_exchange", exchange)

    return kafka_bootstrap, rabbitmq_url, consumer_group_id


def initialize_production_bridge(
    session_factory: Any,
    consumer_group_id: str = "eventing-consumers",
    kafka_topic: str = "events",
) -> tuple[Any, Any]:
    """Initialize production bridge components."""
    from messaging.infrastructure.pubsub.bridge.config import BridgeConfig

    broker, rabbit_broker, rabbit_publisher = initialize_brokers_and_publishers()
    bridge_config = BridgeConfig(
        kafka_topic=kafka_topic,
        rabbitmq_exchange=app_settings.rabbitmq_exchange,
        routing_key_template="{event_type}",
        consumer_group_id=consumer_group_id,
    )
    register_bridge_handler(broker, bridge_config, rabbit_publisher, session_factory)
    return broker, rabbit_broker
