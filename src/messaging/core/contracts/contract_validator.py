"""Event contract version compatibility validator."""

from __future__ import annotations


class ContractViolationError(Exception):
    """Raised when event version is incompatible with consumer."""


def check_version_compatibility(event_version: str, consumer_max_version: str) -> None:
    """Check if event version is compatible with consumer's max version.

    Raises ContractViolationError if event version is incompatible.
    Uses semantic versioning: event version must not exceed consumer's max version.
    """
    event_parts = event_version.split(".")
    consumer_parts = consumer_max_version.split(".")

    event_major = int(event_parts[0])
    event_minor = int(event_parts[1]) if len(event_parts) > 1 else 0

    consumer_major = int(consumer_parts[0])
    consumer_minor = int(consumer_parts[1]) if len(consumer_parts) > 1 else 0

    if event_major > consumer_major:
        msg = (
            f"Incompatible event version: event is v{event_version} but "
            f"consumer only supports up to v{consumer_max_version} (major version mismatch)"
        )
        raise ContractViolationError(msg)

    if event_major == consumer_major and event_minor > consumer_minor:
        msg = (
            f"Incompatible event version: event is v{event_version} but "
            f"consumer only supports up to v{consumer_max_version} (minor version too new)"
        )
        raise ContractViolationError(msg)
