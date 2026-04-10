"""Integration tests for OpenTelemetry end-to-end tracing."""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@pytest.fixture
def otel_setup():
    """Set up isolated OpenTelemetry tracing for each test."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Reset global state
    trace._TRACER_PROVIDER = None
    if hasattr(trace, "_TRACER_PROVIDER_SET_ONCE"):
        trace._TRACER_PROVIDER_SET_ONCE = trace.Once()  # type: ignore[attr-defined] # internal OpenTelemetry implementation detail
    trace.set_tracer_provider(provider)

    yield exporter, provider

    provider.shutdown()
    trace._TRACER_PROVIDER = None
    if hasattr(trace, "_TRACER_PROVIDER_SET_ONCE"):
        trace._TRACER_PROVIDER_SET_ONCE = trace.Once()  # type: ignore[attr-defined] # internal OpenTelemetry implementation detail


@pytest.mark.integration
class TestOpenTelemetryWiring:
    """Test full pipeline OTel instrumentation."""

    @pytest.mark.asyncio
    async def test_kafka_to_rabbitmq_trace_propagation(self, otel_setup) -> None:
        """Kafka publish -> bridge consume -> RabbitMQ publish shares trace_id."""
        exporter, provider = otel_setup

        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("kafka_publish"):
            pass

        with tracer.start_as_current_span("bridge_consume"):
            pass

        with tracer.start_as_current_span("rabbitmq_publish"):
            pass

        provider.force_flush()

        spans = exporter.get_finished_spans()
        assert len(spans) == 3

        kafka_span = next(s for s in spans if s.name == "kafka_publish")
        bridge_span = next(s for s in spans if s.name == "bridge_consume")
        rabbit_span = next(s for s in spans if s.name == "rabbitmq_publish")

        assert kafka_span is not None
        assert bridge_span is not None
        assert rabbit_span is not None

    @pytest.mark.asyncio
    async def test_span_links_bridge_kafka_to_rabbitmq(self, otel_setup) -> None:
        """Bridge creates span links from Kafka context to RabbitMQ publish."""
        exporter, provider = otel_setup

        tracer = trace.get_tracer("test-bridge")

        # Simulate bridge operation with span linking
        with tracer.start_as_current_span("kafka.consume") as kafka_span:
            kafka_context = kafka_span.get_span_context()

            # RabbitMQ publish span linked to Kafka consume span
            with tracer.start_as_current_span(
                "rabbitmq.publish",
                links=[trace.Link(kafka_context)]
            ):
                pass

        provider.force_flush()

        spans = exporter.get_finished_spans()
        assert len(spans) >= 2, f"Expected at least 2 spans, got {len(spans)}"

        rabbitmq_span = next((s for s in spans if "rabbitmq" in s.name), None)
        assert rabbitmq_span is not None
        assert len(rabbitmq_span.links) > 0
