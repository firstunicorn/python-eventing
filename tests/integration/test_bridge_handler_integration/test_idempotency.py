"""Test production bridge handler idempotency."""

import asyncio
import json
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
class TestIdempotency:
    """Test production handler prevents duplicate message processing."""

    @pytest.mark.asyncio
    async def test_production_handler_idempotency(
        self,
        kafka_container,
        rabbitmq_container,
        sqlite_session_factory,
        monkeypatch,
    ) -> None:
        """Test production handler prevents duplicate message processing."""
        kafka_bootstrap, rabbitmq_url = setup_test_containers_config(
            kafka_container, rabbitmq_container, monkeypatch, exchange="test-events-idempotency"
        )

        _, async_session_factory = sqlite_session_factory

        broker, rabbit_broker = initialize_production_bridge(async_session_factory)

        async with broker, rabbit_broker:
            await broker.start()
            await rabbit_broker.start()

            connection = await aio_pika.connect_robust(rabbitmq_url)
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                "test-events-idempotency", ExchangeType.TOPIC, durable=True
            )
            queue = await channel.declare_queue(f"test-queue-{uuid4()}", auto_delete=True)
            await queue.bind(exchange, routing_key="order.#")

            await asyncio.sleep(5)

            producer = Producer({"bootstrap.servers": kafka_bootstrap})
            event_id = f"idempotent-prod-{uuid4()}"
            test_msg = {
                "event_id": event_id,
                "event_type": "order.placed",
                "data": {"order_id": 456},
            }

            producer.produce("events", value=json.dumps(test_msg).encode())
            producer.flush()
            await asyncio.sleep(8)

            producer.produce("events", value=json.dumps(test_msg).encode())
            producer.flush()
            await asyncio.sleep(8)

            messages_received = []
            try:
                msg1 = await asyncio.wait_for(queue.get(timeout=5), timeout=6)
                messages_received.append(json.loads(msg1.body.decode()))
                await msg1.ack()

                try:
                    msg2 = await asyncio.wait_for(queue.get(timeout=5), timeout=6)
                    messages_received.append(json.loads(msg2.body.decode()))
                    await msg2.ack()
                except (TimeoutError, QueueEmpty):
                    pass

            except (TimeoutError, QueueEmpty):
                pytest.fail("First message not received")

            assert len(messages_received) == 1
            assert messages_received[0]["event_id"] == event_id

            await connection.close()
