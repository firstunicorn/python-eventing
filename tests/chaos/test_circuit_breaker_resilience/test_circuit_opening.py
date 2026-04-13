"""Test circuit breaker opening on broker failures."""

import pytest


@pytest.mark.chaos
class TestCircuitOpening:
    """Test circuit opens on broker failure."""

    @pytest.mark.asyncio
    async def test_kafka_circuit_opens_on_broker_down(
        self, kafka_broker_with_circuit_breaker
    ) -> None:
        """Kill Kafka container, circuit opens after publish failures."""
        import asyncio

        from messaging.core.contracts.circuit_breaker import CircuitOpenError
        from messaging.infrastructure.pubsub.kafka_publisher import KafkaEventPublisher

        broker, kafka_container = kafka_broker_with_circuit_breaker
        KafkaEventPublisher(broker)

        circuit_breaker_middleware_factory = broker.middlewares[0]
        circuit_breaker_middleware_instance = circuit_breaker_middleware_factory()
        circuit_breaker = circuit_breaker_middleware_instance._breaker

        assert circuit_breaker.state.value == "closed"

        kafka_container.stop()
        await asyncio.sleep(1)

        for _ in range(4):
            await circuit_breaker.record_failure()
            await asyncio.sleep(0.1)

        assert (
            circuit_breaker.state.value == "open"
        ), f"Expected circuit open after failures, got {circuit_breaker.state.value}"

        with pytest.raises(CircuitOpenError):
            await circuit_breaker.call(lambda: None)
