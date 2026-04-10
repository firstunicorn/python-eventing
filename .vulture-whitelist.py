# Vulture whitelist for intentionally unused code
# Each entry is scoped to specific files/functions to avoid false negatives elsewhere

# === tests/conftest.py:124 ===
# pytest_sessionfinish(session, exitstatus) - exitstatus required by pytest hook signature
exitstatus  # Used in: pytest_sessionfinish hook

# === tests/conftest.py:265 ===
# async_client(skip_broker_in_tests, ...) - fixture parameter used for side effects only
skip_broker_in_tests  # Used in: async_client fixture (sets TESTING_SKIP_BROKER env var)

# === src/messaging/infrastructure/pubsub/broker_config/_factory_helpers.py:24 ===
# === src/messaging/infrastructure/pubsub/rabbit_broker_config/_factory_helpers.py:26 ===
# circuit_breaker_factory(msg, context) - context required by FastStream middleware interface
# These are nested functions inside create_circuit_breaker_factory()
context  # Used in: circuit_breaker_factory nested functions (FastStream signature requirement)
