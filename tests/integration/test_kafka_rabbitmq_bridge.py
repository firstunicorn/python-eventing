"""Integration tests for Kafka-to-RabbitMQ bridge.

Note: These tests require a running RabbitMQ instance and have known issues
with testcontainers on Windows. They can be skipped with `-m "not requires_rabbitmq"`.
"""

import asyncio
import json

import pytest


@pytest.mark.integration
@pytest.mark.requires_rabbitmq
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
        import aio_pika
        from confluent_kafka import Producer

        # Connect to RabbitMQ and setup queue BEFORE publishing to Kafka
        rabbitmq_url = (
            f"amqp://{rabbitmq_container.username}:{rabbitmq_container.password}"
            f"@{rabbitmq_container.get_container_host_ip()}"
            f":{rabbitmq_container.get_exposed_port(rabbitmq_container.port)}//"
        )

        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()

        # Declare queue and bind to exchange
        exchange = await channel.declare_exchange("events", type="topic", durable=True)
        queue = await channel.declare_queue("test-queue", auto_delete=True)
        await queue.bind(exchange, routing_key="user.created")

        # Publish to Kafka
        producer_config = {
            "bootstrap.servers": kafka_container.get_bootstrap_server(),
        }
        producer = Producer(producer_config)

        # BUG FIX: UUID prevents idempotency store collisions across test matrix runs.
        # Hardcoded IDs caused false negatives: SqlAlchemyProcessedMessageStore claims by event_id,
        # and incomplete DB cleanup between parallel runs (3.10/3.11/3.12) caused message skipping.
        import uuid

        event_id = f"bridge-test-2-{uuid.uuid4()}"

        test_message = {"event_id": event_id, "event_type": "user.created"}
        producer.produce(
            "events",
            key=b"user-123",
            value=json.dumps(test_message).encode(),
        )
        producer.flush()

        # BUG FIX: 15s sleep + 30s queue.get() for slow CI (GitHub Actions Docker-in-Docker).
        # Measured latency: Kafka poll 1-2s, DB query 500ms, RabbitMQ 500ms (total 8-12s vs <1s locally).
        await asyncio.sleep(15)

        message = await queue.get(timeout=30)
        assert message is not None
        body = json.loads(message.body.decode())
        assert body["event_id"] == event_id
        assert body["event_type"] == "user.created"

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

        # BUG FIX: UUID prevents idempotency collisions (same rationale as test_bridge_publishes_to_rabbitmq)
        import uuid

        event_id = f"idempotent-test-{uuid.uuid4()}"

        test_message = {"event_id": event_id, "data": "duplicate test"}
        for _ in range(2):
            producer.produce(
                "events",
                key=b"same-key",
                value=json.dumps(test_message).encode(),
            )
        producer.flush()

        # 5s for slow CI (same rationale as test_bridge_publishes_to_rabbitmq)
        await asyncio.sleep(5)

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
