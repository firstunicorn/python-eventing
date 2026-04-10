"""Unit tests for schema evolution and compatibility checking."""

import pytest

from messaging.core.contracts.schema_registry import SchemaEvolutionError, SchemaRegistry


class TestSchemaCompatibility:
    """Test backward/forward compatibility checks."""

    def test_adding_optional_field_is_backward_compatible(self) -> None:
        """Adding optional field passes compatibility check."""
        registry = SchemaRegistry()
        v1_schema = {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        }
        v2_schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "email": {"type": "string"},
            },
            "required": ["user_id"],
        }

        registry.register("user.created", v1_schema, "1.0")
        registry.check_compatibility("user.created", v2_schema)

    def test_removing_required_field_is_breaking(self) -> None:
        """Removing required field raises SchemaEvolutionError."""
        registry = SchemaRegistry()
        v1_schema = {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}, "email": {"type": "string"}},
            "required": ["user_id", "email"],
        }
        v2_schema = {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        }

        registry.register("user.created", v1_schema, "1.0")

        with pytest.raises(SchemaEvolutionError, match=r"[Rr]emoved required field"):
            registry.check_compatibility("user.created", v2_schema)

    def test_renaming_field_is_breaking(self) -> None:
        """Renaming field raises SchemaEvolutionError."""
        registry = SchemaRegistry()
        v1_schema = {
            "type": "object",
            "properties": {"userId": {"type": "integer"}},
            "required": ["userId"],
        }
        v2_schema = {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        }

        registry.register("user.created", v1_schema, "1.0")

        with pytest.raises(SchemaEvolutionError, match=r"[Rr]emoved required field"):
            registry.check_compatibility("user.created", v2_schema)

    def test_changing_field_type_is_breaking(self) -> None:
        """Changing field type raises SchemaEvolutionError."""
        registry = SchemaRegistry()
        v1_schema = {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
        }
        v2_schema = {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
        }

        registry.register("user.created", v1_schema, "1.0")

        with pytest.raises(SchemaEvolutionError, match=r"[Tt]ype changed.*user_id"):
            registry.check_compatibility("user.created", v2_schema)
