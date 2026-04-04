"""Property-based tests for event serialization and envelopes."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from messaging.core.contracts import BaseEvent, EventEnvelopeFormatter, EventRegistry


class ExampleEvent(BaseEvent):  # pylint: disable=too-many-ancestors
    """Concrete generated event used for property tests."""

    event_type: str = "gamification.XPAwarded"
    aggregate_id: str
    source: str
    xp_delta: int


_SAFE_TEXT = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122),
    min_size=1,
    max_size=24,
)
_JSON_SCALARS = st.one_of(
    st.booleans(),
    st.integers(min_value=0, max_value=10_000),
    st.text(alphabet=st.characters(min_codepoint=48, max_codepoint=122), max_size=24),
)


@given(
    aggregate_id=_SAFE_TEXT,
    source=_SAFE_TEXT,
    xp_delta=st.integers(min_value=1, max_value=10_000),
    metadata=st.dictionaries(_SAFE_TEXT, _JSON_SCALARS, max_size=4),
)
def test_registry_round_trip_preserves_generated_payloads(
    aggregate_id: str,
    source: str,
    xp_delta: int,
    metadata: dict[str, bool | int | str],
) -> None:
    """Serialized property-generated events should deserialize without drift."""
    event = ExampleEvent(
        aggregate_id=aggregate_id,
        source=source,
        xp_delta=xp_delta,
        metadata=metadata,
    )
    registry = EventRegistry()
    registry.register(ExampleEvent)

    restored = registry.deserialize(event.to_message())

    assert restored.model_dump(mode="json", by_alias=True) == event.to_message()


@given(default_source=_SAFE_TEXT)
def test_envelope_formatter_honors_configured_source(default_source: str) -> None:
    """CloudEvents envelopes should use the formatter source override consistently."""
    event = ExampleEvent(aggregate_id="user-123", source="gamification-service", xp_delta=5)
    formatter = EventEnvelopeFormatter(default_source=default_source)

    envelope = formatter.format(event)

    assert envelope["source"] == default_source
    assert envelope["data"]["eventType"] == event.event_type
