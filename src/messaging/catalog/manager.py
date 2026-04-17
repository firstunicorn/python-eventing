"""Event catalog manager for Git-based catalog repositories."""

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore  # Backport for Python <3.11

from messaging.config.event_catalog_settings import EventCatalogSettings


class EventCatalogManager:
    """Manages local cache of external event catalog repository.

    Handles Git clone/pull operations, TOML parsing, and catalog
    validation against event types and service names.
    """

    def __init__(self, settings: EventCatalogSettings) -> None:
        """Initialize catalog manager with settings."""
        self.settings = settings
        self.local_path = Path(settings.local_path)
        self._last_refresh: datetime | None = None
        self._catalog_data: dict | None = None

    async def ensure_catalog(self) -> dict | None:
        """Ensure catalog is cloned and up-to-date.

        Returns catalog data dict or None if no catalog configured.
        """
        if self.settings.repo_url is None:
            return None

        if not self.local_path.exists():
            await self._clone_catalog()
        elif self._needs_refresh():
            await self._pull_catalog()

        if self._catalog_data is None:
            self._load_catalog()

        return self._catalog_data

    def _needs_refresh(self) -> bool:
        """Check if catalog needs refreshing based on interval."""
        if self._last_refresh is None:
            return True

        now = datetime.now(UTC)
        refresh_interval = timedelta(seconds=self.settings.refresh_interval)
        return now - self._last_refresh > refresh_interval

    async def _clone_catalog(self) -> None:
        """Clone catalog repository to local path."""
        self.local_path.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                self.settings.branch,
                str(self.settings.repo_url),
                str(self.local_path),
            ],
            check=True,
            shell=False,
            capture_output=True,
        )
        self._last_refresh = datetime.now(UTC)

    async def _pull_catalog(self) -> None:
        """Pull latest changes from catalog repository."""
        subprocess.run(
            ["git", "pull"],
            cwd=str(self.local_path),
            check=True,
            shell=False,
            capture_output=True,
        )
        self._last_refresh = datetime.now(UTC)

    def _load_catalog(self) -> None:
        """Load catalog TOML files into memory."""
        events_file = self.local_path / "events.toml"
        services_file = self.local_path / "services.toml"

        self._catalog_data = {
            "events": self._load_toml(events_file) if events_file.exists() else {},
            "services": (
                self._load_toml(services_file) if services_file.exists() else {}
            ),
        }

    def _load_toml(self, path: Path) -> dict:
        """Load TOML file."""
        with path.open("rb") as f:
            return tomllib.load(f)

    def validate_event_type(self, event_type: str) -> tuple[bool, str]:
        """Validate event type against catalog.

        Returns:
            (is_valid, message) tuple
            - is_valid: True if valid, False if should reject
            - message: Error message or warning message
        """
        if self._catalog_data is None:
            return (True, "")

        events = self._catalog_data.get("events", {})
        event_key = f"events.{event_type}"

        if event_key not in events:
            if self.settings.strict_mode:
                msg = (
                    f"Event type '{event_type}' not found in catalog\n"
                    f"Strict mode is enabled. Add this event to the catalog "
                    f"or disable strict mode."
                )
                return (False, msg)
            msg = (
                f"Warning: Event type '{event_type}' not found in catalog. "
                f"Consider adding it to maintain event registry."
            )
            return (True, msg)

        return (True, "")

    def validate_service_name(self, service_name: str) -> tuple[bool, str]:
        """Validate service name against catalog.

        Returns:
            (is_valid, message) tuple
            - is_valid: True if valid, False if should reject
            - message: Error message or warning message
        """
        if self._catalog_data is None:
            return (True, "")

        services = self._catalog_data.get("services", {})
        service_key = f"services.{service_name}"

        if service_key not in services:
            if self.settings.strict_mode:
                msg = (
                    f"Service '{service_name}' not found in catalog\n"
                    f"Strict mode is enabled. Add this service to the catalog "
                    f"or disable strict mode."
                )
                return (False, msg)
            msg = (
                f"Warning: Service '{service_name}' not found in catalog. "
                f"Consider adding it to maintain service registry."
            )
            return (True, msg)

        return (True, "")
