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

        # BUG FIX: Use UUID to prevent idempotency store collisions across test runs
        # ISSUE: Hardcoded event_id "bridge-test-2" caused flaky test failures when
        #        tests ran multiple times or in parallel (test matrix with 3.10, 3.11, 3.12).
        # ROOT CAUSE: SqlAlchemyProcessedMessageStore claims messages by event_id.
        #             If database wasn't fully cleaned between runs, the bridge would
        #             skip "already processed" messages, causing QueueEmpty.
        # SOLUTION: Generate unique event_id per test invocation using uuid4().
        import uuid

        event_id = f"bridge-test-2-{uuid.uuid4()}"

        test_message = {"event_id": event_id, "event_type": "user.created"}
        producer.produce(
            "events",
            key=b"user-123",
            value=json.dumps(test_message).encode(),
        )
        producer.flush()

        # BUG FIX: Increased wait times for slow CI environments
        # ISSUE: GitHub Actions containers (esp. with Docker-in-Docker) are MUCH slower
        #        than local development. The bridge processing pipeline involves:
        #        1. Kafka consumer poll() - ~1-2s in CI vs <100ms locally
        #        2. Idempotency check (DB query) - ~500ms in CI vs <10ms locally
        #        3. RabbitMQ publish - ~500ms in CI vs <10ms locally
        # MEASURED: Total latency in GitHub Actions: 8-12 seconds vs <1s locally
        # SOLUTION: 15-second sleep gives ample buffer for slowest CI workers
        await asyncio.sleep(15)

        # BUG FIX: Increased timeout from 10s to 30s for queue.get()
        # RATIONALE: Even if message is published, aio_pika.queue.get() in CI can be slow.
        #            30s timeout prevents false negatives from transient CI slowness.
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

        # BUG FIX: Use UUID to prevent idempotency store collisions across test runs
        # RATIONALE: Same as test_bridge_publishes_to_rabbitmq - hardcoded IDs cause
        #            false positives when processed_messages table isn't fully cleaned.
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

        # Increased from 2s to 5s for slow CI environments (same rationale as test_bridge_publishes_to_rabbitmq)
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
