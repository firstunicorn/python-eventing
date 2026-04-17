"""Main application settings composition.

This module defines the `Settings` class that loads configuration from
environment variables. It extends reusable base configurations from the
toolkit and eventing-specific mixins.

See Also
--------
- messaging.main : Where settings are used during app creation
- fastapi_config_patterns : The toolkit base settings classes
"""

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from fastapi_config_patterns import BaseDatabaseSettings, BaseFastAPISettings
from messaging.config.event_catalog_settings import EventCatalogSettings
from messaging.config.kafka_settings import KafkaSettings
from messaging.config.rabbitmq_settings import RabbitMQSettings


class Settings(
    BaseFastAPISettings,
    BaseDatabaseSettings,
    KafkaSettings,
    RabbitMQSettings,
    EventCatalogSettings,
):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="EVENTING_",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = Field(default="eventing", description="Public service identifier.")
    api_prefix: str = Field(default="/api/v1", description="Prefix applied to the HTTP API.")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/eventing",
        description="Async SQLAlchemy database URL.",
    )


settings = Settings()
