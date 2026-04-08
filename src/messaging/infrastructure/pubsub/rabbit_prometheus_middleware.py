"""Custom Prometheus middleware for RabbitMQ via FastStream."""

from __future__ import annotations

from typing import Any

from faststream import BaseMiddleware, StreamMessage
from prometheus_client import CollectorRegistry, Counter


class RabbitPrometheusMiddleware(BaseMiddleware):
    """Minimal Prometheus metrics for RabbitMQ via FastStream middleware."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """Initialize middleware with Prometheus registry."""
        self._registry = registry
        self._counter = Counter(
            "events_consume_total",
            "Total events consumed",
            ["broker", "status"],
            registry=registry,
        )

    async def consume_scope(
        self, call_next: Any, msg: StreamMessage[Any]
    ) -> Any:
        """Wrap consume with Prometheus metrics."""
        try:
            result = await call_next(msg)
            self._counter.labels(broker="rabbitmq", status="success").inc()
            return result
        except Exception:
            self._counter.labels(broker="rabbitmq", status="failure").inc()
            raise
