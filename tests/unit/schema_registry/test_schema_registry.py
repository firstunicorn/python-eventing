"""Unit tests for schema registry storage and versioning."""

import pytest

from messaging.core.contracts.schema_registry import SchemaRegistry, UnknownSchemaVersionError


class TestSchemaRegistryBasics:
    """Test schema registration and retrieval."""

    def test_register_and_get_schema(self) -> None:
        """Register schema, retrieve by exact version."""
        registry = SchemaRegistry()
        schema = {"type": "object", "properties": {"user_id": {"type": "integer"}}}

        registry.register("user.created", schema, "1.0")

        retrieved = registry.get("user.created", "1.0")
        assert retrieved == schema

    def test_register_multiple_versions(self) -> None:
        """Register two versions, retrieve each independently."""
        registry = SchemaRegistry()
        v1_schema = {"type": "object", "properties": {"id": {"type": "integer"}}}
        v2_schema = {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "email": {"type": "string"}},
        }

        registry.register("user.created", v1_schema, "1.0")
        registry.register("user.created", v2_schema, "2.0")

        assert registry.get("user.created", "1.0") == v1_schema
        assert registry.get("user.created", "2.0") == v2_schema

    def test_get_latest_returns_highest_version(self) -> None:
        """get_latest() returns most recent version."""
        registry = SchemaRegistry()
        v1 = {"type": "object", "properties": {"a": {"type": "string"}}}
        v2 = {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "integer"}}}

        registry.register("order.placed", v1, "1.0")
        registry.register("order.placed", v2, "2.1")

        version, schema = registry.get_latest("order.placed")
        assert version == "2.1"
        assert schema == v2

    def test_get_nonexistent_version_raises(self) -> None:
        """Requesting unknown version raises UnknownSchemaVersionError."""
        registry = SchemaRegistry()
        registry.register("user.created", {}, "1.0")

        with pytest.raises(UnknownSchemaVersionError, match=r"[Uu]nknown version"):
            registry.get("user.created", "2.0")

    def test_get_nonexistent_event_type_raises(self) -> None:
        """Requesting unknown event type raises UnknownSchemaVersionError."""
        registry = SchemaRegistry()

        with pytest.raises(UnknownSchemaVersionError, match="unknown.event"):
            registry.get("unknown.event", "1.0")
