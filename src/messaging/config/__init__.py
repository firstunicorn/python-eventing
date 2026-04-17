"""Runtime settings for the eventing service."""

from messaging.config.base_settings import Settings, settings
from messaging.config.event_catalog_settings import EventCatalogSettings

__all__ = ["EventCatalogSettings", "Settings", "settings"]
