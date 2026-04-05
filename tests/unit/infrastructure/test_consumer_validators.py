"""Unit tests for consumer validation functions."""

from __future__ import annotations

import pytest

from messaging.infrastructure.pubsub.consumer_base.consumer_validators import (
    extract_event_id,
    validate_consumer_name,
)


class TestValidateConsumerName:
    """Tests for validate_consumer_name normalization."""

    def test_valid_name_returned_stripped(self) -> None:
        assert validate_consumer_name("  order-service  ") == "order-service"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="consumer_name must not be empty"):
            validate_consumer_name("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="consumer_name must not be empty"):
            validate_consumer_name("   ")


class TestExtractEventId:
    """Tests for extract_event_id from message payloads."""

    def test_camelcase_key(self) -> None:
        assert extract_event_id({"eventId": "evt-123"}) == "evt-123"

    def test_snakecase_key(self) -> None:
        assert extract_event_id({"event_id": "evt-456"}) == "evt-456"

    def test_camelcase_preferred_over_snakecase(self) -> None:
        assert extract_event_id({"eventId": "a", "event_id": "b"}) == "a"

    def test_strips_whitespace(self) -> None:
        assert extract_event_id({"eventId": "  evt-789  "}) == "evt-789"

    def test_non_string_converted(self) -> None:
        assert extract_event_id({"eventId": 123}) == "123"

    def test_missing_both_keys_raises(self) -> None:
        with pytest.raises(ValueError, match="must include eventId"):
            extract_event_id({"foo": "bar"})

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            extract_event_id({"eventId": "   "})

    def test_none_value_raises(self) -> None:
        with pytest.raises(ValueError, match="must include eventId"):
            extract_event_id({"eventId": None})
