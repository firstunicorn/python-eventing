"""Integration test for RabbitMQ publishing by bridge."""

import asyncio
import json
import uuid

import pytest


@pytest.mark.integration
@pytest.mark.requires_rabbitmq
class TestRabbitMQPublishing:
    """Test RabbitMQ publishing by the bridge."""

    @pytest.mark.asyncio
    async def test_bridge_publishes_to_rabbitmq(
        self, kafka_container, rabbitmq_container, async_client_with_kafka
    ) -> None:
        """Bridge publishes consumed Kafka events to RabbitMQ with routing key."""
        import aio_pika
        from confluent_kafka import Producer

        rabbitmq_url = (
            f"amqp://{rabbitmq_container.username}:{rabbitmq_container.password}"
            f"@{rabbitmq_container.get_container_host_ip()}"
            f":{rabbitmq_container.get_exposed_port(rabbitmq_container.port)}//"
        )

        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()

        exchange = await channel.declare_exchange("events", type="topic", durable=True)
        queue = await channel.declare_queue("test-queue", auto_delete=True)
        await queue.bind(exchange, routing_key="user.created")

        producer_config = {
            "bootstrap.servers": kafka_container.get_bootstrap_server(),
        }
        producer = Producer(producer_config)

        event_id = f"bridge-test-2-{uuid.uuid4()}"

        test_message = {"event_id": event_id, "event_type": "user.created"}
        producer.produce(
            "events",
            key=b"user-123",
            value=json.dumps(test_message).encode(),
        )
        producer.flush()

        await asyncio.sleep(25)

        message = await queue.get(timeout=45)
        assert message is not None
        body = json.loads(message.body.decode())
        assert body["event_id"] == event_id
        assert body["event_type"] == "user.created"

        await connection.close()
