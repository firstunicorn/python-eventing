"""JSON schema payload validator."""

from __future__ import annotations

from typing import Any

import jsonschema  # type: ignore[import-untyped]

from messaging.core.contracts.schema_registry import SchemaRegistry


class SchemaValidationError(Exception):
    """Raised when payload fails JSON schema validation."""


class JsonSchemaValidator:
    """Validate event payloads against registered JSON schemas."""

    def __init__(self, registry: SchemaRegistry) -> None:
        """Initialize validator with schema registry."""
        self._registry = registry

    def validate(self, event_type: str, version: str, payload: dict[str, Any]) -> None:
        """Validate payload against registered schema."""
        schema = self._registry.get(event_type, version)
        try:
            jsonschema.validate(instance=payload, schema=schema)
        except jsonschema.ValidationError as exc:
            msg = f"Schema validation failed for {event_type} v{version}: {exc.message}"
            raise SchemaValidationError(msg) from exc
