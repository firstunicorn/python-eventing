"""Unit tests for Prometheus metrics exporter."""

from typing import Any

import pytest
from faststream import StreamMessage
from prometheus_client import CollectorRegistry

from messaging.infrastructure.pubsub.rabbit_prometheus_middleware import RabbitPrometheusMiddleware


class TestPrometheusExporter:
    """Test dispatch hook emits metrics."""

    @pytest.mark.asyncio
    async def test_rabbit_middleware_creates_metrics(self) -> None:
        """RabbitPrometheusMiddleware increments counters on consume."""
        registry = CollectorRegistry()
        middleware = RabbitPrometheusMiddleware(registry=registry)

        async def call_next(msg: StreamMessage[Any]) -> str:
            return "processed"

        msg = StreamMessage(raw_message=b"test", body={"test": "data"})
        result = await middleware.consume_scope(call_next, msg)

        assert result == "processed"

        metrics_text = registry.get_sample_value(
            "events_consume_total", {"broker": "rabbitmq", "status": "success"}
        )
        assert metrics_text == 1.0

    @pytest.mark.asyncio
    async def test_rabbit_middleware_increments_on_success(self) -> None:
        """Successful consume increments success label."""
        registry = CollectorRegistry()
        middleware = RabbitPrometheusMiddleware(registry=registry)

        async def call_next(msg: StreamMessage[Any]) -> str:
            return "ok"

        msg = StreamMessage(raw_message=b"test", body={"test": "data"})
        await middleware.consume_scope(call_next, msg)

        value = registry.get_sample_value(
            "events_consume_total", {"broker": "rabbitmq", "status": "success"}
        )
        assert value == 1.0

    @pytest.mark.asyncio
    async def test_rabbit_middleware_increments_on_failure(self) -> None:
        """Failed consume increments failure label."""
        registry = CollectorRegistry()
        middleware = RabbitPrometheusMiddleware(registry=registry)

        async def call_next(msg: StreamMessage[Any]) -> None:
            msg = "processing failed"
            raise ValueError(msg)

        msg = StreamMessage(raw_message=b"test", body={"test": "data"})

        with pytest.raises(ValueError):
            await middleware.consume_scope(call_next, msg)

        value = registry.get_sample_value(
            "events_consume_total", {"broker": "rabbitmq", "status": "failure"}
        )
        assert value == 1.0
