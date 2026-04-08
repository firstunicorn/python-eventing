"""Unit tests for JSON schema payload validation."""

import pytest

from messaging.core.contracts.schema_registry import SchemaRegistry
from messaging.core.contracts.schema_validator import (
    JsonSchemaValidator,
    SchemaValidationError,
)


class TestJsonSchemaValidation:
    """Test payload validation against registered schemas."""

    def test_valid_payload_passes(self) -> None:
        """Valid payload matching schema passes validation."""
        registry = SchemaRegistry()
        schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "email": {"type": "string"},
            },
            "required": ["user_id", "email"],
        }
        registry.register("user.created", schema, "1.0")
        validator = JsonSchemaValidator(registry)

        payload = {"user_id": 123, "email": "test@example.com"}
        validator.validate("user.created", "1.0", payload)

    def test_missing_required_field_raises(self) -> None:
        """Missing required field raises SchemaValidationError."""
        registry = SchemaRegistry()
        schema = {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        }
        registry.register("user.created", schema, "1.0")
        validator = JsonSchemaValidator(registry)

        payload = {"email": "test@example.com"}

        with pytest.raises(SchemaValidationError, match="user_id.*required"):
            validator.validate("user.created", "1.0", payload)

    def test_wrong_type_raises(self) -> None:
        """Wrong field type raises SchemaValidationError."""
        registry = SchemaRegistry()
        schema = {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
        }
        registry.register("user.created", schema, "1.0")
        validator = JsonSchemaValidator(registry)

        payload = {"user_id": "not-an-integer"}

        with pytest.raises(SchemaValidationError, match=r"Schema validation failed.*user.created"):
            validator.validate("user.created", "1.0", payload)

    def test_extra_fields_allowed_for_forward_compatibility(self) -> None:
        """Extra unknown fields are allowed (forward compatibility)."""
        registry = SchemaRegistry()
        schema = {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "additionalProperties": True,
        }
        registry.register("user.created", schema, "1.0")
        validator = JsonSchemaValidator(registry)

        payload = {"user_id": 123, "future_field": "new-data"}
        validator.validate("user.created", "1.0", payload)
