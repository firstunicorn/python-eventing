# Pydantic settings not overridden by monkeypatch.setenv

**Date:** 2026-04-11
**Status:** Fixed ✅
**Severity:** High — tests used production broker URLs instead of test containers

## Symptom

Tests failed to connect to test Kafka/RabbitMQ containers. App connected to production brokers or failed entirely despite `monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", ...)` being called.

## Root cause

Pydantic `SettingsConfigDict(env_prefix="EVENTING_")` loads settings at import time. Two issues:

1. `monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", ...)` sets wrong env var — Pydantic looks for `EVENTING_KAFKA_BOOTSTRAP_SERVERS` due to prefix
2. Even with correct env var, settings singleton already instantiated at import time, so env changes ignored

## Fix

Replace `monkeypatch.setenv()` with `monkeypatch.setattr()` to directly mutate the settings singleton:

```python
# WRONG:
monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", kafka_bootstrap)

# CORRECT:
from messagekit.config import settings as app_settings
monkeypatch.setattr(app_settings, "kafka_bootstrap_servers", kafka_bootstrap)
```

`setattr()` bypasses env var resolution entirely and mutates the already-loaded Pydantic object.

## Files changed

- `tests/conftest.py` — `async_client_with_kafka` fixture

## Lessons

- Pydantic settings with `env_prefix` require prefixed env vars (`EVENTING_*`)
- `monkeypatch.setenv()` doesn't affect already-instantiated Pydantic models
- `monkeypatch.setattr()` on the settings singleton is the reliable approach for test overrides
