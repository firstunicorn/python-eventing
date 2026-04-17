"""Unit tests for EventCatalogManager."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from messaging.catalog.manager import EventCatalogManager
from messaging.config.event_catalog_settings import EventCatalogSettings


class TestEventCatalogManagerInit:
    """Test EventCatalogManager initialization."""

    def test_init_with_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Manager initializes with provided settings."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "https://github.com/org/catalog.git")
        monkeypatch.setenv("EVENT_CATALOG_LOCAL_PATH", "/tmp/catalog")
        settings = EventCatalogSettings()

        manager = EventCatalogManager(settings)

        assert manager.settings == settings
        assert manager.local_path == Path("/tmp/catalog")
        assert manager._last_refresh is None
        assert manager._catalog_data is None


class TestEventCatalogManagerEnsureCatalog:
    """Test catalog ensuring and loading."""

    @pytest.mark.asyncio
    async def test_ensure_catalog_no_repo_url(self) -> None:
        """Returns None when no repo_url configured."""
        settings = EventCatalogSettings()  # No repo_url
        manager = EventCatalogManager(settings)

        result = await manager.ensure_catalog()

        assert result is None

    @pytest.mark.asyncio
    @patch("messaging.catalog.manager.subprocess.run")
    async def test_ensure_catalog_first_clone(
        self, mock_run: Mock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Clones repository on first access."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "https://github.com/org/catalog.git")
        monkeypatch.setenv("EVENT_CATALOG_LOCAL_PATH", str(tmp_path / "catalog"))
        settings = EventCatalogSettings()
        manager = EventCatalogManager(settings)

        # Create empty TOML files after "clone"
        def create_toml_files(*args, **kwargs):  # noqa: ARG001
            manager.local_path.mkdir(parents=True, exist_ok=True)
            (manager.local_path / "events.toml").write_text("")
            (manager.local_path / "services.toml").write_text("")

        mock_run.side_effect = create_toml_files

        result = await manager.ensure_catalog()

        assert result == {"events": {}, "services": {}}
        mock_run.assert_called_once()
        assert manager._last_refresh is not None


class TestEventCatalogManagerValidation:
    """Test event type and service name validation."""

    def test_validate_event_type_no_catalog(self) -> None:
        """Validation passes when no catalog loaded."""
        settings = EventCatalogSettings()
        manager = EventCatalogManager(settings)

        is_valid, message = manager.validate_event_type("orders.order.created")

        assert is_valid is True
        assert message == ""

    def test_validate_event_type_found_in_catalog(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Validation passes when event type found in catalog."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "https://github.com/org/catalog.git")
        settings = EventCatalogSettings()
        manager = EventCatalogManager(settings)
        manager._catalog_data = {
            "events": {"events.orders.order.created": {"owner_service": "order-service"}},
            "services": {},
        }

        is_valid, message = manager.validate_event_type("orders.order.created")

        assert is_valid is True
        assert message == ""

    def test_validate_event_type_not_found_warn_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Validation warns when event type not found (warn mode)."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "https://github.com/org/catalog.git")
        monkeypatch.setenv("EVENT_CATALOG_STRICT_MODE", "false")
        settings = EventCatalogSettings()
        manager = EventCatalogManager(settings)
        manager._catalog_data = {"events": {}, "services": {}}

        is_valid, message = manager.validate_event_type("orders.order.created")

        assert is_valid is True
        assert "Warning" in message
        assert "orders.order.created" in message
