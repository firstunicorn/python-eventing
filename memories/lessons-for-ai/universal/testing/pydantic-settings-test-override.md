# Pydantic settings override in tests — setattr vs setenv

**Date:** 2026-04-11
**Status:** Documented ✅
**Severity:** High — tests use production config instead of test containers

## Problem

`monkeypatch.setenv()` doesn't override Pydantic settings when:
1. Settings use `env_prefix` (e.g., `EVENTING_KAFKA_BOOTSTRAP_SERVERS` instead of `KAFKA_BOOTSTRAP_SERVERS`)
2. Settings are already instantiated at import time (before monkeypatch runs)

## Root cause

Pydantic `BaseSettings` loads configuration at import time from environment variables. By the time test fixtures run and call `monkeypatch.setenv()`, the settings singleton is already instantiated with production values.

Additionally, `env_prefix="EVENTING_"` means Pydantic looks for `EVENTING_KAFKA_BOOTSTRAP_SERVERS`, not `KAFKA_BOOTSTRAP_SERVERS`.

## Solution

Use `monkeypatch.setattr()` to directly mutate the settings singleton:

```python
# WRONG — doesn't work:
monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# CORRECT — bypasses env var resolution:
from messagekit.config import settings as app_settings
monkeypatch.setattr(app_settings, "kafka_bootstrap_servers", "localhost:9092")
```

## Why this works

`setattr()` mutates the already-loaded Pydantic object directly, bypassing environment variable resolution entirely. The settings singleton is updated in-place.

## Applicable to

Any project using Pydantic `BaseSettings` with `env_prefix` or import-time loading.
