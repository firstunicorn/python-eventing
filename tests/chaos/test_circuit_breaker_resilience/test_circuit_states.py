"""Test circuit breaker state transitions."""

from datetime import UTC, datetime

import pytest


@pytest.mark.chaos
class TestCircuitStateTransitions:
    """Test circuit state transitions and recovery."""

    @pytest.mark.asyncio
    async def test_kafka_circuit_half_opens_on_timeout(
        self, kafka_broker_with_circuit_breaker
    ) -> None:
        """After timeout, circuit transitions to half-open state."""
        import asyncio

        from messaging.core.contracts.circuit_breaker import CircuitState

        broker, kafka_container = kafka_broker_with_circuit_breaker

        circuit_breaker_middleware_factory = broker.middlewares[0]
        circuit_breaker_middleware_instance = circuit_breaker_middleware_factory()
        circuit_breaker = circuit_breaker_middleware_instance._breaker

        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

        await asyncio.sleep(2.5)

        assert circuit_breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_kafka_successful_publish_closes_circuit(
        self, kafka_broker_with_circuit_breaker
    ) -> None:
        """Successful publish after recovery closes circuit."""
        import asyncio
        from uuid import uuid4

        from messaging.core.contracts.base_event import BaseEvent
        from messaging.core.contracts.circuit_breaker import CircuitState
        from messaging.infrastructure.pubsub.kafka_publisher import KafkaEventPublisher

        broker, kafka_container = kafka_broker_with_circuit_breaker
        publisher = KafkaEventPublisher(broker)
        circuit_breaker_middleware_factory = broker.middlewares[0]
        circuit_breaker_middleware_instance = circuit_breaker_middleware_factory()
        circuit_breaker = circuit_breaker_middleware_instance._breaker

        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

        await asyncio.sleep(2.5)
        assert circuit_breaker.state == CircuitState.HALF_OPEN

        test_event = BaseEvent(
            event_id=uuid4(),
            event_type="test.event",
            aggregate_id="test",
            occurred_at=datetime.now(UTC),
            source="chaos-test",
        )

        await publisher.publish(test_event.to_message())

        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_rabbitmq_circuit_integration_placeholder(self) -> None:
        """RabbitMQ circuit breaker integration (placeholder for future work)."""
        assert True
