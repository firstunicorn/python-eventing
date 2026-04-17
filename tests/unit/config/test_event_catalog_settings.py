"""Unit tests for EventCatalogSettings configuration."""

import pytest

from messaging.config.event_catalog_settings import EventCatalogSettings


class TestEventCatalogSettingsDefaults:
    """Test default values for EventCatalogSettings."""

    def test_default_values(self) -> None:
        """All fields should have sensible defaults."""
        settings = EventCatalogSettings()

        assert settings.repo_url is None
        assert settings.branch == "main"
        assert settings.local_path == "./.event-catalog"
        assert settings.refresh_interval == 3600  # 1 hour
        assert settings.strict_mode is False

    def test_repo_url_optional(self) -> None:
        """repo_url is optional and defaults to None."""
        settings = EventCatalogSettings()
        assert settings.repo_url is None


class TestEventCatalogSettingsFromEnv:
    """Test loading EventCatalogSettings from environment variables."""

    def test_load_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings should load from EVENT_CATALOG_* environment variables."""
        monkeypatch.setenv(
            "EVENT_CATALOG_REPO_URL", "https://github.com/test-org/event-catalog.git"
        )
        monkeypatch.setenv("EVENT_CATALOG_BRANCH", "production")
        monkeypatch.setenv("EVENT_CATALOG_LOCAL_PATH", "/var/cache/catalog")
        monkeypatch.setenv("EVENT_CATALOG_REFRESH_INTERVAL", "1800")
        monkeypatch.setenv("EVENT_CATALOG_STRICT_MODE", "true")

        settings = EventCatalogSettings()

        # HttpUrl may normalize with or without trailing slash
        assert "test-org/event-catalog.git" in str(settings.repo_url)
        assert settings.branch == "production"
        assert settings.local_path == "/var/cache/catalog"
        assert settings.refresh_interval == 1800
        assert settings.strict_mode is True

    def test_partial_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Partial env vars should work with defaults for missing values."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "https://github.com/test-org/catalog.git")
        monkeypatch.setenv("EVENT_CATALOG_STRICT_MODE", "true")

        settings = EventCatalogSettings()

        # HttpUrl may normalize with or without trailing slash
        assert "test-org/catalog.git" in str(settings.repo_url)
        assert settings.branch == "main"  # Default
        assert settings.local_path == "./.event-catalog"  # Default
        assert settings.refresh_interval == 3600  # Default
        assert settings.strict_mode is True


class TestEventCatalogSettingsValidation:
    """Test validation of EventCatalogSettings fields."""

    def test_repo_url_must_be_valid_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """repo_url must be a valid HTTP(S) URL if provided."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "not-a-valid-url")

        with pytest.raises((ValueError, TypeError)):  # Pydantic validation error
            EventCatalogSettings()

    def test_repo_url_accepts_https(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """repo_url should accept HTTPS URLs."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "https://github.com/org/catalog.git")

        settings = EventCatalogSettings()
        assert "github.com/org/catalog.git" in str(settings.repo_url)

    def test_repo_url_accepts_http(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """repo_url should accept HTTP URLs."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "http://internal-git/catalog.git")

        settings = EventCatalogSettings()
        assert "internal-git/catalog.git" in str(settings.repo_url)

    def test_refresh_interval_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """refresh_interval should accept positive integers from env."""
        monkeypatch.setenv("EVENT_CATALOG_REFRESH_INTERVAL", "60")

        settings = EventCatalogSettings()
        assert settings.refresh_interval == 60

    def test_strict_mode_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """strict_mode should accept boolean values from env."""
        monkeypatch.setenv("EVENT_CATALOG_STRICT_MODE", "true")
        settings_true = EventCatalogSettings()

        monkeypatch.setenv("EVENT_CATALOG_STRICT_MODE", "false")
        settings_false = EventCatalogSettings()

        assert settings_true.strict_mode is True
        assert settings_false.strict_mode is False


class TestEventCatalogSettingsUseCases:
    """Test real-world usage scenarios."""

    def test_development_mode_no_catalog(self) -> None:
        """Development mode: no catalog configured."""
        settings = EventCatalogSettings()

        assert settings.repo_url is None
        assert settings.strict_mode is False

    def test_staging_mode_warn_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Staging mode: catalog configured, warn mode."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "https://github.com/org/catalog.git")
        monkeypatch.setenv("EVENT_CATALOG_BRANCH", "main")
        monkeypatch.setenv("EVENT_CATALOG_STRICT_MODE", "false")
        monkeypatch.setenv("EVENT_CATALOG_REFRESH_INTERVAL", "1800")

        settings = EventCatalogSettings()

        assert settings.repo_url is not None
        assert settings.strict_mode is False
        assert settings.refresh_interval == 1800

    def test_production_mode_strict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Production mode: catalog configured, strict mode."""
        monkeypatch.setenv("EVENT_CATALOG_REPO_URL", "https://github.com/org/catalog.git")
        monkeypatch.setenv("EVENT_CATALOG_BRANCH", "production")
        monkeypatch.setenv("EVENT_CATALOG_STRICT_MODE", "true")
        monkeypatch.setenv("EVENT_CATALOG_REFRESH_INTERVAL", "3600")
        monkeypatch.setenv("EVENT_CATALOG_LOCAL_PATH", "/var/cache/event-catalog")

        settings = EventCatalogSettings()

        assert settings.repo_url is not None
        assert settings.branch == "production"
        assert settings.strict_mode is True
        assert settings.refresh_interval == 3600
        assert settings.local_path == "/var/cache/event-catalog"
