"""Test that FakeKafkaBroker signature matches real FastStream KafkaBroker."""

from __future__ import annotations

import inspect

from faststream.confluent import KafkaBroker

from tests.unit.infrastructure.conftest import FakeKafkaBroker
from tests.unit.infrastructure.test_fake_broker_contract.helpers import normalize_annotation


def test_fake_kafka_broker_matches_real_faststream_signature() -> None:
    """Ensure FakeKafkaBroker stays in sync with FastStream KafkaBroker.

    WHAT THIS TEST DOES
    ===================
    1. Extracts method signature from real FastStream KafkaBroker.publish()
    2. Extracts method signature from our FakeKafkaBroker.publish()
    3. Compares parameter names, defaults, and type annotations
    4. Fails with detailed diff if any mismatch is found

    WHY SKIP CERTAIN PARAMETERS
    ============================
    We skip detailed type checking for:
    - message: FastStream uses SendableMessage (complex union), we use dict[str, object]
              (more explicit for tests, behaviorally compatible)
    - key: FastStream allows Any for flexibility, we're more strict with bytes | None
           (stricter typing is acceptable for test fakes)
    - headers: Similar flexibility difference

    These differences are intentional and acceptable for test doubles.

    WHEN THIS TEST SHOULD FAIL
    ===========================
    - FastStream adds a new parameter to publish()
    - FastStream changes a default value
    - FastStream renames a parameter
    - FastStream removes a parameter

    If this test fails, update FakeKafkaBroker to match the new signature,
    then verify all tests still pass.
    """
    real_sig = inspect.signature(KafkaBroker.publish)
    fake_sig = inspect.signature(FakeKafkaBroker.publish)

    real_params = set(real_sig.parameters.keys())
    fake_params = set(fake_sig.parameters.keys())

    # First check: Do both methods have the same parameter names?
    assert real_params == fake_params, (
        f"Parameter mismatch between FakeKafkaBroker and real KafkaBroker:\n"
        f"  Real params: {sorted(real_params)}\n"
        f"  Fake params: {sorted(fake_params)}\n"
        f"  Missing in fake: {sorted(real_params - fake_params)}\n"
        f"  Extra in fake: {sorted(fake_params - real_params)}"
    )

    # Second check: Do parameters have matching defaults and types?
    for param_name in real_sig.parameters:
        # Skip self parameter (always different)
        # Skip complex types where test fake intentionally differs
        if param_name in ("self", "message", "key", "headers"):
            continue

        real_param = real_sig.parameters[param_name]
        fake_param = fake_sig.parameters[param_name]

        # Check default values match
        assert real_param.default == fake_param.default, (
            f"Default value mismatch for parameter '{param_name}':\n"
            f"  Real: {real_param.default}\n"
            f"  Fake: {fake_param.default}"
        )

        # Check type annotations match (normalized for comparison)
        real_ann = normalize_annotation(real_param.annotation)
        fake_ann = normalize_annotation(fake_param.annotation)

        assert real_ann == fake_ann, (
            f"Type annotation mismatch for parameter '{param_name}':\n"
            f"  Real: {real_param.annotation} (normalized: {real_ann})\n"
            f"  Fake: {fake_param.annotation} (normalized: {fake_ann})"
        )
