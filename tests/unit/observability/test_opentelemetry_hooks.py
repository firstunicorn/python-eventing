"""Unit tests for OpenTelemetry hooks."""

from typing import Any

import pytest
from faststream import StreamMessage
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from messaging.infrastructure.observability.otel_middleware import (
    OpenTelemetryMiddleware,
)


@pytest.fixture
def isolated_tracer():
    """Set up isolated tracer for each test to prevent state contamination."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Reset global state completely
    trace._TRACER_PROVIDER = None
    if hasattr(trace, "_TRACER_PROVIDER_SET_ONCE"):
        trace._TRACER_PROVIDER_SET_ONCE = trace.Once()  # type: ignore[attr-defined] # internal OpenTelemetry implementation detail
    trace.set_tracer_provider(provider)

    yield exporter, provider

    provider.force_flush()
    provider.shutdown()
    trace._TRACER_PROVIDER = None
    if hasattr(trace, "_TRACER_PROVIDER_SET_ONCE"):
        trace._TRACER_PROVIDER_SET_ONCE = trace.Once()  # type: ignore[attr-defined] # internal OpenTelemetry implementation detail


class TestOpenTelemetryHooks:
    """Test basic OTel span creation."""

    @pytest.mark.asyncio
    async def test_opentelemetry_middleware_creates_spans_with_attributes(
        self, isolated_tracer
    ) -> None:
        """OpenTelemetry middleware creates spans with messaging attributes."""
        exporter, provider = isolated_tracer

        middleware = OpenTelemetryMiddleware(tracer_name="test-tracer")

        async def call_next(msg: StreamMessage[Any]) -> str:
            return "processed"

        msg = StreamMessage(raw_message=b"test", body={"test": "data"})
        result = await middleware.consume_scope(call_next, msg)

        assert result == "processed"

        provider.force_flush()

        spans = exporter.get_finished_spans()
        assert len(spans) >= 1

        found_span = next((s for s in spans if s.name == "faststream.consume"), None)
        assert found_span is not None, "Expected faststream.consume span not found"

        attrs = dict(found_span.attributes or {})
        assert attrs.get("messaging.system") == "faststream"
        assert attrs.get("messaging.operation") == "consume"
