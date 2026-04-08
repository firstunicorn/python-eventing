"""Basic OpenTelemetry instrumentation for FastStream."""

from __future__ import annotations

from typing import Any

from faststream import BaseMiddleware, StreamMessage
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


class OpenTelemetryMiddleware(BaseMiddleware):
    """Minimal OpenTelemetry tracing for FastStream consumers."""

    def __init__(self, tracer_name: str = "faststream") -> None:
        """Initialize middleware with tracer."""
        self._tracer = trace.get_tracer(tracer_name)

    async def consume_scope(
        self, call_next: Any, msg: StreamMessage[Any]
    ) -> Any:
        """Wrap consume with OpenTelemetry span."""
        with self._tracer.start_as_current_span("faststream.consume") as span:
            span.set_attribute("messaging.system", "faststream")
            span.set_attribute("messaging.operation", "consume")

            try:
                result = await call_next(msg)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise
