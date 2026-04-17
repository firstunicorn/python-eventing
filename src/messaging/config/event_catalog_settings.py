"""Event catalog configuration settings."""

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class EventCatalogSettings(BaseSettings):
    """Configuration for external event catalog repository.

    Organizations can host their own event catalog in Git and point
    the library to it for validation and discovery.

    Example .env:
        EVENT_CATALOG_REPO_URL=https://github.com/your-org/event-catalog.git
        EVENT_CATALOG_BRANCH=main
        EVENT_CATALOG_LOCAL_PATH=./.event-catalog
        EVENT_CATALOG_REFRESH_INTERVAL=3600
        EVENT_CATALOG_STRICT_MODE=false
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="EVENT_CATALOG_",
        case_sensitive=False,
        extra="ignore",
    )

    repo_url: HttpUrl | None = Field(
        default=None,
        description="Git URL for event catalog (e.g., https://github.com/org/event-catalog.git)",
        validation_alias="EVENT_CATALOG_REPO_URL",
    )

    branch: str = Field(
        default="main",
        description="Branch name to fetch from catalog repo",
        validation_alias="EVENT_CATALOG_BRANCH",
    )

    local_path: str = Field(
        default="./.event-catalog",
        description="Local path to clone/cache the catalog",
        validation_alias="EVENT_CATALOG_LOCAL_PATH",
    )

    refresh_interval: int = Field(
        default=3600,  # 1 hour
        description="How often to refresh catalog from Git (seconds)",
        validation_alias="EVENT_CATALOG_REFRESH_INTERVAL",
    )

    strict_mode: bool = Field(
        default=False,
        description="If True, reject events not in catalog. If False, warn only.",
        validation_alias="EVENT_CATALOG_STRICT_MODE",
    )
