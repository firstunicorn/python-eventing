"""Test production handler exception nack behavior."""

import asyncio
import json
from typing import Any
from uuid import uuid4

import aio_pika
import pytest
from aio_pika import ExchangeType
from aio_pika.exceptions import QueueEmpty
from confluent_kafka import Producer

from .setup_helpers import initialize_production_bridge, setup_test_containers_config


@pytest.mark.integration
@pytest.mark.requires_kafka
@pytest.mark.requires_rabbitmq
class TestExceptionNack:
    """Test production handler exception triggers nack."""

    @pytest.mark.asyncio
    async def test_bridge_handler_exception_path_triggers_nack(
        self,
        kafka_container,
        rabbitmq_container,
        sqlite_session_factory,
        monkeypatch,
    ) -> None:
        """Test generic exceptions trigger nack and do NOT publish."""
        kafka_bootstrap, rabbitmq_url, consumer_group_id = setup_test_containers_config(
            kafka_container,
            rabbitmq_container,
            monkeypatch,
            exchange="test-events-exception-nack",
            consumer_group_id="exception-nack-test-group",
        )

        _, async_session_factory = sqlite_session_factory

        from messaging.infrastructure.pubsub.bridge import consumer as bridge_module

        original_handle = bridge_module.BridgeConsumer.handle_message

        async def exploding_handle(_consumer_self: Any, message: dict[str, Any]) -> None:
            raise RuntimeError("Forced exception for coverage")

        monkeypatch.setattr(bridge_module.BridgeConsumer, "handle_message", exploding_handle)

        broker, rabbit_broker = initialize_production_bridge(
            async_session_factory, consumer_group_id=consumer_group_id
        )

        async with broker, rabbit_broker:
            await broker.start()
            await rabbit_broker.start()

            connection = await aio_pika.connect_robust(rabbitmq_url)
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                "test-events-exception-nack", ExchangeType.TOPIC, durable=True
            )
            queue = await channel.declare_queue(f"test-queue-{uuid4()}", auto_delete=True)
            await queue.bind(exchange, routing_key="#")

            await asyncio.sleep(5)

            producer = Producer({"bootstrap.servers": kafka_bootstrap})
            event_id = f"exception-test-{uuid4()}"
            message = {
                "event_id": event_id,
                "event_type": "order.created",
                "payload": {"order_id": 999},
                "timestamp": "2026-01-01T00:00:00Z",
            }
            producer.produce("events", value=json.dumps(message).encode())
            producer.flush()

            await asyncio.sleep(8)

            with pytest.raises(QueueEmpty):
                await queue.get(timeout=2.0)

            monkeypatch.setattr(bridge_module.BridgeConsumer, "handle_message", original_handle)
            await connection.close()
