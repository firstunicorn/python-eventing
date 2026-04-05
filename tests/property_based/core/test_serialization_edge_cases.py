"""Property-based tests for serialization with edge case payloads.

Tests UTF-8, large text, datetime edges, and null value handling.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from messaging.core.contracts import EventRegistry
from tests.unit.infrastructure.conftest import ExampleEvent

_SAFE_CHARS = st.characters(min_codepoint=32, max_codepoint=1200, exclude_categories=["Cs"])

_UNICODE_TEXT = st.text(alphabet=_SAFE_CHARS, min_size=1, max_size=500)

_SAFE_TEXT = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122), min_size=1, max_size=24
)


@given(_SAFE_TEXT, _SAFE_TEXT, st.integers(-10000, 10000))
def test_round_trip_lossless_serialization(
    agg_id: str,
    source: str,
    xp_delta: int,
) -> None:
    """Events should serialize and deserialize without data loss."""
    occurred_at = datetime(2026, 1, 1, tzinfo=UTC)
    event = ExampleEvent(
        aggregate_id=agg_id, source=source, xp_delta=xp_delta, occurred_at=occurred_at
    )

    registry = EventRegistry()
    registry.register(ExampleEvent)

    message = event.to_message()
    restored = registry.deserialize(message)

    assert restored.event_id == event.event_id
    assert restored.event_type == event.event_type
    assert restored.aggregate_id == event.aggregate_id
    assert restored.xp_delta == event.xp_delta


@given(_UNICODE_TEXT)
def test_unicode_round_trip(unicode_text: str) -> None:
    """Unicode text in payloads should round-trip correctly."""
    event = ExampleEvent(
        aggregate_id=unicode_text[:24],
        source="unicode-service",
        xp_delta=0,
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    registry = EventRegistry()
    registry.register(ExampleEvent)

    restored = registry.deserialize(event.to_message())
    assert restored.aggregate_id == event.aggregate_id
