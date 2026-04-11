# ruff: noqa
# Vulture whitelist for intentionally unused code
# Each entry is scoped to specific files/functions to avoid false negatives elsewhere

# === tests/conftest.py:127 ===
# pytest_sessionfinish(session, exitstatus) - exitstatus required by pytest hook signature
# RATIONALE: pytest hook interface REQUIRES exitstatus parameter even if unused
# REFERENCE: https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_sessionfinish
exitstatus  # Used in: pytest_sessionfinish hook

# === tests/conftest.py:307 ===
# async_client(skip_broker_in_tests, ...) - fixture parameter used for side effects only
# RATIONALE: Parameter triggers skip_broker_in_tests fixture execution via pytest dependency injection
#            The fixture sets TESTING_SKIP_BROKER env var but doesn't return a value used by async_client
skip_broker_in_tests  # Used in: async_client fixture (sets TESTING_SKIP_BROKER env var)

# === src/messaging/infrastructure/pubsub/broker_config/_factory_helpers.py:34 ===
# === src/messaging/infrastructure/pubsub/rabbit_broker_config/_factory_helpers.py:36 ===
# circuit_breaker_factory(msg, context) - context required by FastStream middleware interface
# RATIONALE: FastStream middleware factory signature REQUIRES (msg, context) parameters
#            Cannot remove even though unused (framework interface requirement)
# REFERENCE: https://faststream.ag2.ai/latest/getting-started/middlewares/middleware/
# NOTE: ARG001 is suppressed inline in source. Vulture still detects as unused (expected).
context  # Used in: circuit_breaker_factory nested functions (FastStream signature requirement)
