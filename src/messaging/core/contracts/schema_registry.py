"""JSON schema registry for event type versioning and compatibility."""

from __future__ import annotations

from typing import Any


class UnknownSchemaVersionError(Exception):
    """Raised when requesting unknown event type or version."""


class SchemaEvolutionError(Exception):
    """Raised when schema change breaks compatibility."""


class SchemaRegistry:
    """Store and version JSON schemas for event types."""

    def __init__(self) -> None:
        """Initialize empty schema registry."""
        self._schemas: dict[str, dict[str, dict[str, Any]]] = {}

    def register(self, event_type: str, schema: dict[str, Any], version: str) -> None:
        """Register schema for event type at specific version."""
        if event_type not in self._schemas:
            self._schemas[event_type] = {}
        self._schemas[event_type][version] = schema

    def get(self, event_type: str, version: str) -> dict[str, Any]:
        """Get schema for event type at specific version."""
        if event_type not in self._schemas:
            msg = f"Unknown event type: {event_type}"
            raise UnknownSchemaVersionError(msg)
        if version not in self._schemas[event_type]:
            msg = f"Unknown version {version} for event type {event_type}"
            raise UnknownSchemaVersionError(msg)
        return self._schemas[event_type][version]

    def get_latest(self, event_type: str) -> tuple[str, dict[str, Any]]:
        """Get most recent schema version for event type."""
        if event_type not in self._schemas:
            msg = f"Unknown event type: {event_type}"
            raise UnknownSchemaVersionError(msg)
        versions = list(self._schemas[event_type].keys())
        latest_version = max(versions, key=lambda v: tuple(map(int, v.split("."))))
        return latest_version, self._schemas[event_type][latest_version]

    def check_compatibility(self, event_type: str, new_schema: dict[str, Any]) -> None:
        """Check if new schema is compatible with existing versions."""
        if event_type not in self._schemas:
            return
        latest_version, latest_schema = self.get_latest(event_type)
        old_required = set(latest_schema.get("required", []))
        new_required = set(new_schema.get("required", []))
        old_props = set(latest_schema.get("properties", {}).keys())
        new_props = set(new_schema.get("properties", {}).keys())
        removed_required = old_required - new_required
        if removed_required:
            msg = f"Removed required field(s): {removed_required}"
            raise SchemaEvolutionError(msg)
        renamed = (old_required - new_props) | (new_required - old_props)
        if renamed:
            msg = f"Field(s) renamed or removed: {renamed}"
            raise SchemaEvolutionError(msg)
        for prop in old_props & new_props:
            old_type = latest_schema.get("properties", {}).get(prop, {}).get("type")
            new_type = new_schema.get("properties", {}).get(prop, {}).get("type")
            if old_type and new_type and old_type != new_type:
                msg = f"Type changed for field {prop}: {old_type} -> {new_type}"
                raise SchemaEvolutionError(msg)
