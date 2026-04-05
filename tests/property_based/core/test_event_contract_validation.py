"""Property-based tests for event contract/schema validation.

Tests that the event system correctly validates schemas and rejects invalid payloads.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from messaging.core.contracts import BaseEvent, EventRegistry, UnknownEventTypeError
from tests.unit.infrastructure.conftest import ExampleEvent

_VALID_KEYS = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10)


@given(
    st.dictionaries(
        _VALID_KEYS,
        st.one_of(st.integers(), st.floats(allow_nan=False), st.booleans()),
        max_size=5,
    )
)
def test_deserialize_rejects_unregistered_types(payload: dict[str, Any]) -> None:
    """EventRegistry should raise UnknownEventTypeError for unregistered types."""
    registry = EventRegistry()
    with pytest.raises(UnknownEventTypeError):
        registry.deserialize(payload)


@given(st.one_of(st.integers(), st.floats(allow_nan=False), st.booleans(), st.none()))
def test_deserialize_rejects_bad_event_type_values(bad_type: Any) -> None:
    """Registry should reject payloads with non-string eventType values."""
    registry = EventRegistry()
    registry.register(ExampleEvent)
    payload = {"eventType": bad_type}
    with pytest.raises(Exception):  # noqa: B017,PT011 - any exception acceptable
        registry.deserialize(payload)


def test_deserialize_accepts_valid_payload_with_extra_fields() -> None:
    """Valid payloads with extra unknown fields should be accepted."""
    registry = EventRegistry()
    registry.register(ExampleEvent)

    payload = {
        "eventType": "gamification.XPAwarded",
        "aggregateId": "user-999",
        "source": "test-service",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "eventId": "00000000-0000-0000-0000-000000000001",
        "xpDelta": 10,
        "extraField": "should_be_ignored",
    }

    event = registry.deserialize(payload)
    assert isinstance(event, ExampleEvent)


def test_from_dict_rejects_missing_event_type() -> None:
    """BaseEvent should reject payloads without eventType."""
    with pytest.raises(Exception):  # noqa: B017,PT011 - pydantic validation error type varies
        BaseEvent.model_validate({"aggregateId": "x"})
