"""End-to-end integration tests for catalog validation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from messaging.catalog.manager import EventCatalogManager
from messaging.config.event_catalog_settings import EventCatalogSettings
from messaging.core.contracts.base_event import BaseEvent


class SampleEvent(BaseEvent):
    """Sample event for testing."""

    aggregate_id: str = "test-123"


class TestCatalogValidationE2E:
    """End-to-end catalog validation tests."""

    @pytest.mark.asyncio
    async def test_valid_event_in_catalog_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Events with types found in catalog should pass."""
        catalog_path = tmp_path / "catalog"
        catalog_path.mkdir()
        (catalog_path / "events.toml").write_text(
            '[events."orders.order.created"]\n'
            'owner_service = "order-service"\n'
            'owner_team = "commerce"\n'
        )
        (catalog_path / "services.toml").write_text(
            '[services.order-service]\n'
            'team = "commerce"\n'
            'events_published = ["orders.order.created"]\n'
        )

        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "https://github.com/org/catalog.git")
        monkeypatch.setenv("EVENT_CATALOG_LOCAL_PATH", str(catalog_path))
        monkeypatch.setenv("EVENT_CATALOG_STRICT_MODE", "true")

        settings = EventCatalogSettings()
        manager = EventCatalogManager(settings)

        # Manually load catalog without Git operations
        manager._catalog_data = {
            "events": {"events.orders.order.created": {"owner_service": "order-service"}},
            "services": {"services.order-service": {"team": "commerce"}},
        }

        # Mock the global catalog manager in base_event module
        import messaging.core.contracts.base_event as base_event_module

        original_manager = base_event_module._catalog_manager
        base_event_module._catalog_manager = manager

        try:
            # Should pass - event type and source are in catalog
            event = SampleEvent(
                event_type="orders.order.created", source="order-service"
            )
            assert event.event_type == "orders.order.created"
            assert event.source == "order-service"
        finally:
            base_event_module._catalog_manager = original_manager

    @pytest.mark.asyncio
    async def test_invalid_event_type_strict_mode_rejects(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Events not in catalog should be rejected in strict mode."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "https://github.com/org/catalog.git")
        monkeypatch.setenv("EVENT_CATALOG_STRICT_MODE", "true")

        settings = EventCatalogSettings()
        manager = EventCatalogManager(settings)

        # Empty catalog
        manager._catalog_data = {"events": {}, "services": {"services.order-service": {}}}

        import messaging.core.contracts.base_event as base_event_module

        original_manager = base_event_module._catalog_manager
        base_event_module._catalog_manager = manager

        try:
            with pytest.raises(ValidationError, match="not found in catalog"):
                SampleEvent(
                    event_type="orders.order.created", source="order-service"
                )
        finally:
            base_event_module._catalog_manager = original_manager

    def test_no_catalog_configured_format_only(self) -> None:
        """Without catalog, only format validation should run."""
        import messaging.core.contracts.base_event as base_event_module

        original_manager = base_event_module._catalog_manager
        base_event_module._catalog_manager = None

        try:
            # Valid format should pass
            event = SampleEvent(
                event_type="orders.order.created", source="order-service"
            )
            assert event.event_type == "orders.order.created"

            # Invalid format should fail
            with pytest.raises(ValidationError, match="event_type must match pattern"):
                SampleEvent(event_type="INVALID", source="order-service")
        finally:
            base_event_module._catalog_manager = original_manager
