"""Unit tests for event format validation (event_type and source)."""

import pytest
from pydantic import ValidationError

from messaging.core.contracts import BaseEvent


class ValidEvent(BaseEvent):
    """Test event with valid naming."""

    event_type: str = "orders.order.created"
    aggregate_id: str = "test-123"
    source: str = "order-service"


class TestEventTypeValidation:
    """Test event_type format validation."""

    def test_valid_event_type_with_hyphens(self) -> None:
        """Valid event types with hyphens in entity/event segments should pass."""

        class TestEvent(BaseEvent):
            aggregate_id: str = "test-123"
            source: str = "order-service"

        event = TestEvent(event_type="orders.order-item.created")
        assert event.event_type == "orders.order-item.created"

    def test_valid_event_type_simple(self) -> None:
        """Valid simple event type should pass."""
        event = ValidEvent()
        assert event.event_type == "orders.order.created"

    def test_invalid_event_type_uppercase(self) -> None:
        """Event types with uppercase letters should be rejected."""

        class TestEvent(BaseEvent):
            aggregate_id: str = "test-123"
            source: str = "order-service"

        with pytest.raises(ValidationError, match="event_type must match pattern"):
            TestEvent(event_type="Orders.Order.Created")

    def test_invalid_event_type_spaces(self) -> None:
        """Event types with spaces should be rejected."""

        class TestEvent(BaseEvent):
            aggregate_id: str = "test-123"
            source: str = "order-service"

        with pytest.raises(ValidationError, match="event_type must match pattern"):
            TestEvent(event_type="orders.order created.event")

    def test_invalid_event_type_underscores(self) -> None:
        """Event types with underscores should be rejected."""

        class TestEvent(BaseEvent):
            aggregate_id: str = "test-123"
            source: str = "order-service"

        with pytest.raises(ValidationError, match="event_type must match pattern"):
            TestEvent(event_type="orders.order_created.event")

    def test_invalid_event_type_two_segments(self) -> None:
        """Event types with only two segments should be rejected."""

        class TestEvent(BaseEvent):
            aggregate_id: str = "test-123"
            source: str = "order-service"

        with pytest.raises(ValidationError, match="event_type must match pattern"):
            TestEvent(event_type="orders.created")

    def test_invalid_event_type_special_chars(self) -> None:
        """Event types with special characters should be rejected."""

        class TestEvent(BaseEvent):
            aggregate_id: str = "test-123"
            source: str = "order-service"

        with pytest.raises(ValidationError, match="event_type must match pattern"):
            TestEvent(event_type="orders.order@created.event")

    def test_error_message_includes_expected_format(self) -> None:
        """Error message should guide developers to correct format."""

        class TestEvent(BaseEvent):
            aggregate_id: str = "test-123"
            source: str = "order-service"

        with pytest.raises(
            ValidationError,
            match="Expected: lowercase with dots",
        ):
            TestEvent(event_type="INVALID")


class TestSourceValidation:
    """Test source format validation."""

    def test_valid_source_simple(self) -> None:
        """Valid simple source should pass."""
        event = ValidEvent()
        assert event.source == "order-service"

    def test_valid_source_with_numbers(self) -> None:
        """Valid source with numbers should pass."""

        class TestEvent(BaseEvent):
            event_type: str = "orders.order.created"
            aggregate_id: str = "test-123"

        event = TestEvent(source="order-service-v2")
        assert event.source == "order-service-v2"

    def test_invalid_source_uppercase(self) -> None:
        """Source with uppercase letters should be rejected."""

        class TestEvent(BaseEvent):
            event_type: str = "orders.order.created"
            aggregate_id: str = "test-123"

        with pytest.raises(ValidationError, match="source must be lowercase-with-hyphens"):
            TestEvent(source="Order-Service")

    def test_invalid_source_spaces(self) -> None:
        """Source with spaces should be rejected."""

        class TestEvent(BaseEvent):
            event_type: str = "orders.order.created"
            aggregate_id: str = "test-123"

        with pytest.raises(ValidationError, match="source must be lowercase-with-hyphens"):
            TestEvent(source="order service")

    def test_invalid_source_underscores(self) -> None:
        """Source with underscores should be rejected."""

        class TestEvent(BaseEvent):
            event_type: str = "orders.order.created"
            aggregate_id: str = "test-123"

        with pytest.raises(ValidationError, match="source must be lowercase-with-hyphens"):
            TestEvent(source="order_service")

    def test_invalid_source_starts_with_number(self) -> None:
        """Source starting with number should be rejected."""

        class TestEvent(BaseEvent):
            event_type: str = "orders.order.created"
            aggregate_id: str = "test-123"

        with pytest.raises(ValidationError, match="source must be lowercase-with-hyphens"):
            TestEvent(source="2order-service")

    def test_invalid_source_special_chars(self) -> None:
        """Source with special characters should be rejected."""

        class TestEvent(BaseEvent):
            event_type: str = "orders.order.created"
            aggregate_id: str = "test-123"

        with pytest.raises(ValidationError, match="source must be lowercase-with-hyphens"):
            TestEvent(source="order@service")

    def test_error_message_includes_expected_format(self) -> None:
        """Error message should guide developers to correct format."""

        class TestEvent(BaseEvent):
            event_type: str = "orders.order.created"
            aggregate_id: str = "test-123"

        with pytest.raises(
            ValidationError,
            match="Expected: lowercase, hyphens, numbers",
        ):
            TestEvent(source="INVALID")
