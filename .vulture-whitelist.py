# ruff: noqa
# Vulture whitelist for intentionally unused code

# === tests/conftest.py:127 ===
# pytest_sessionfinish(session, exitstatus) - required by pytest hook signature
# REFERENCE: https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_sessionfinish
exitstatus  # Used in: pytest_sessionfinish hook

# === tests/conftest.py:307 ===
# async_client(skip_broker_in_tests, ...) - fixture parameter used for side effects only
# Triggers skip_broker_in_tests fixture execution via pytest dependency injection
skip_broker_in_tests  # Used in: async_client fixture (sets TESTING_SKIP_BROKER env var)

# === src/messaging/infrastructure/pubsub/broker_config/_factory_helpers.py:34 ===
# === src/messaging/infrastructure/pubsub/rabbit_broker_config/_factory_helpers.py:36 ===
# circuit_breaker_factory(msg, context) - required by FastStream middleware interface
# REFERENCE: https://faststream.ag2.ai/latest/getting-started/middlewares/middleware/
# NOTE: ARG001 suppressed inline in source. Vulture still detects as unused (expected).
context  # Used in: circuit_breaker_factory nested functions (FastStream signature requirement)
