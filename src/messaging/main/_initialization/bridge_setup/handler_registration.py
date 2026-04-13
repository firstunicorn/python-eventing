"""Kafka bridge handler registration with FastStream."""

from typing import Any

from faststream import AckPolicy
from faststream.confluent import KafkaBroker
from faststream.confluent.annotations import KafkaMessage

from messaging.infrastructure.pubsub.bridge.config import BridgeConfig
from messaging.infrastructure.pubsub.rabbit.publisher import RabbitEventPublisher

from .message_processor import process_kafka_message


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

    @broker.subscriber(
        bridge_config.kafka_topic,
        ack_policy=AckPolicy.MANUAL,
        group_id=bridge_config.consumer_group_id,
    )
    async def handle_kafka_event(message: dict[str, Any], msg: KafkaMessage) -> None:
        """Bridge handler: consume from Kafka, forward to RabbitMQ.

        Args:
            message: Kafka message dict containing event_id and event_type
            msg: KafkaMessage object for manual acknowledgment control
        """
        await process_kafka_message(
            message=message,
            msg=msg,
            session_factory=session_factory,
            rabbit_publisher=rabbit_publisher,
            routing_key_template=bridge_config.routing_key_template,
        )
