"""Unit tests for consumer helper functions."""

from __future__ import annotations

import pytest

from messaging.infrastructure.pubsub.consumer_base.consumer_helpers import extract_event_id


class TestExtractEventId:
    """Tests for extract_event_id helper extraction logic."""

    def test_camelcase_key(self) -> None:
        assert extract_event_id({"eventId": "evt-001"}) == "evt-001"

    def test_snakecase_key(self) -> None:
        assert extract_event_id({"event_id": "evt-002"}) == "evt-002"

    def test_strips_whitespace(self) -> None:
        assert extract_event_id({"eventId": "  x  "}) == "x"

    def test_missing_keys_raises(self) -> None:
        with pytest.raises(ValueError, match="must include eventId"):
            extract_event_id({"other": "data"})

    def test_both_missing_raises(self) -> None:
        with pytest.raises(ValueError, match="must include eventId"):
            extract_event_id({"eventId": None, "event_id": None})

    def test_camelcase_preferred(self) -> None:
        assert extract_event_id({"eventId": "a", "event_id": "b"}) == "a"
