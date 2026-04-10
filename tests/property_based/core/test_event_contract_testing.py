"""Property-based tests for event contract testing with version enforcement."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from messaging.core.contracts.contract_validator import (
    ContractViolationError,
    check_version_compatibility,
)


@pytest.mark.property_based
class TestEventContractTesting:
    """Test version enforcement using Hypothesis."""

    @given(
        event_version=st.sampled_from(["1.0", "1.5", "2.0", "2.3", "3.0"]),
        consumer_version=st.sampled_from(["1.9", "2.0", "2.5", "3.0"]),
    )
    def test_incompatible_major_version_rejected(
        self, event_version: str, consumer_version: str
    ) -> None:
        """Consumer rejects events with incompatible version."""
        event_parts = event_version.split(".")
        consumer_parts = consumer_version.split(".")
        event_major, event_minor = int(event_parts[0]), int(event_parts[1])
        consumer_major, consumer_minor = int(consumer_parts[0]), int(consumer_parts[1])

        incompatible = (
            event_major > consumer_major
            or (event_major == consumer_major and event_minor > consumer_minor)
        )

        if incompatible:
            with pytest.raises(ContractViolationError):
                check_version_compatibility(event_version, consumer_version)
        else:
            check_version_compatibility(event_version, consumer_version)

    @given(
        major=st.integers(min_value=1, max_value=5),
        event_minor=st.integers(min_value=0, max_value=9),
        consumer_minor=st.integers(min_value=0, max_value=9),
    )
    def test_compatible_minor_version_accepted(
        self, major: int, event_minor: int, consumer_minor: int
    ) -> None:
        """Consumer accepts events with compatible minor version bumps."""
        event_version = f"{major}.{event_minor}"
        consumer_version = f"{major}.{consumer_minor}"

        if event_minor <= consumer_minor:
            check_version_compatibility(event_version, consumer_version)
        else:
            with pytest.raises(ContractViolationError):
                check_version_compatibility(event_version, consumer_version)

    @given(
        event_version=st.from_regex(r"[1-9]\.\d+", fullmatch=True),
        consumer_version=st.from_regex(r"[1-9]\.\d+", fullmatch=True),
    )
    def test_contract_violation_raised_on_incompatibility(
        self, event_version: str, consumer_version: str
    ) -> None:
        """ContractViolationError raised for incompatible versions."""
        event_major = int(event_version.split(".")[0])
        consumer_major = int(consumer_version.split(".")[0])

        if event_major > consumer_major:
            with pytest.raises(ContractViolationError):
                check_version_compatibility(event_version, consumer_version)
