"""Adapters from app settings to python-outbox-core config.

This module provides `build_outbox_config`, a utility function that translates
the application's Pydantic `Settings` into the `OutboxConfig` model expected by
the `python-outbox-core` library.

See also
--------
- eventing.config.Settings : The application settings
- eventing.infrastructure.outbox.outbox_worker : The worker that uses this config
"""

from eventing.config import Settings
from python_outbox_core import OutboxConfig


def build_outbox_config(settings: Settings) -> OutboxConfig:
    """Build the outbox worker config from app settings."""
    return OutboxConfig(
        batch_size=settings.outbox_batch_size,
        poll_interval_seconds=settings.outbox_poll_interval_seconds,
        max_retry_count=settings.outbox_max_retry_count,
        retry_backoff_multiplier=settings.outbox_retry_backoff_multiplier,
    )
