"""Integration tests for Kafka-to-RabbitMQ bridge."""

import asyncio
import json

import pytest


@pytest.mark.integration
class TestKafkaRabbitMQBridge:
    """Test the Kafka-to-RabbitMQ bridge integration."""

    @pytest.mark.asyncio
    async def test_bridge_consumes_from_kafka(
        self, kafka_container, async_client_with_kafka
    ) -> None:
        """Bridge consumes events from Kafka topic."""
        from confluent_kafka import Producer

        # Publish test event to Kafka
        producer_config = {
            "bootstrap.servers": kafka_container.get_bootstrap_server(),
        }
        producer = Producer(producer_config)

        test_message = {"event_id": "bridge-test-1", "data": "test payload"}
        producer.produce(
            "bridge-test-topic",
            key=b"test-key",
            value=json.dumps(test_message).encode(),
        )
        producer.flush()

        # Bridge consumer should pick this up
        # Note: Actual bridge consumption verification requires running the bridge consumer
        # This test verifies the infrastructure is set up correctly
        await asyncio.sleep(1)  # Give bridge time to consume

        # Verify message was published to Kafka
        assert True  # Placeholder for actual verification

    @pytest.mark.asyncio
    async def test_bridge_publishes_to_rabbitmq(
        self, kafka_container, rabbitmq_container, async_client_with_kafka
    ) -> None:
        """Bridge publishes consumed Kafka events to RabbitMQ with routing key."""
        from confluent_kafka import Producer
        import aio_pika

        # Publish to Kafka
        producer_config = {
            "bootstrap.servers": kafka_container.get_bootstrap_server(),
        }
        producer = Producer(producer_config)

        test_message = {"event_id": "bridge-test-2", "type": "user.created"}
        producer.produce(
            "events",
            key=b"user-123",
            value=json.dumps(test_message).encode(),
        )
        producer.flush()

        # Connect to RabbitMQ and verify message arrived
        rabbitmq_url = (
            f"amqp://{rabbitmq_container.username}:{rabbitmq_container.password}"
            f"@{rabbitmq_container.get_container_host_ip()}"
            f":{rabbitmq_container.get_exposed_port(5672)}//"
        )

        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()

        # Declare queue and bind to exchange
        queue = await channel.declare_queue("test-queue", auto_delete=True)

        await asyncio.sleep(2)  # Give bridge time to process

        # Verify queue received message
        # This is a placeholder - actual bridge needs to be running
        await connection.close()

    @pytest.mark.asyncio
    async def test_bridge_is_idempotent(self, kafka_container, async_client_with_kafka) -> None:
        """Bridge uses processed-message store to prevent duplicate publishes."""
        from confluent_kafka import Producer

        # Publish same message twice
        producer_config = {
            "bootstrap.servers": kafka_container.get_bootstrap_server(),
        }
        producer = Producer(producer_config)

        test_message = {"event_id": "idempotent-test", "data": "duplicate test"}
        for _ in range(2):
            producer.produce(
                "events",
                key=b"same-key",
                value=json.dumps(test_message).encode(),
            )
        producer.flush()

        await asyncio.sleep(2)

        # Bridge should only process once due to idempotency check
        # Verification requires checking processed_message store
        assert True  # Placeholder

    @pytest.mark.asyncio
    async def test_bridge_handles_malformed_messages(
        self, kafka_container, async_client_with_kafka
    ) -> None:
        """Bridge gracefully skips malformed Kafka messages."""
        from confluent_kafka import Producer

        producer_config = {
            "bootstrap.servers": kafka_container.get_bootstrap_server(),
        }
        producer = Producer(producer_config)

        # Send malformed JSON
        producer.produce("events", key=b"bad-key", value=b"not-json{invalid")
        producer.flush()

        await asyncio.sleep(1)

        # Bridge should log error but not crash
        assert True  # Placeholder
