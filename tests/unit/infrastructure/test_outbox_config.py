"""Unit tests for build_outbox_config mapping."""

from __future__ import annotations

from types import SimpleNamespace

from messaging.infrastructure.outbox.outbox_config import build_outbox_config


def test_build_outbox_config_maps_fields() -> None:
    """Should map all settings to OutboxConfig correctly."""
    settings = SimpleNamespace(
        outbox_batch_size=25,
        outbox_poll_interval_seconds=5,
        outbox_max_retry_count=3,
        outbox_retry_backoff_multiplier=2.0,
    )
    config = build_outbox_config(settings)  # type: ignore[arg-type]

    assert config.batch_size == 25
    assert config.poll_interval_seconds == 5
    assert config.max_retry_count == 3
    assert config.retry_backoff_multiplier == 2.0


def test_build_outbox_config_min_values() -> None:
    """Should handle minimum configuration values."""
    settings = SimpleNamespace(
        outbox_batch_size=1,
        outbox_poll_interval_seconds=1,
        outbox_max_retry_count=0,
        outbox_retry_backoff_multiplier=1.0,
    )
    config = build_outbox_config(settings)  # type: ignore[arg-type]
    assert config.max_retry_count == 0
