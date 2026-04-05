"""Helper functions for Kafka consumer message processing.

Pure functions extracted from Kafka consumer classes for extracting event
identifiers and validating message payloads.
"""

from __future__ import annotations

from typing import Any


def extract_event_id(message: dict[str, Any]) -> str:
    """Extract event_id from a message payload.

    Checks for both 'eventId' (camelCase) and 'event_id' (snake_case) keys.
    The extracted value is stripped of whitespace and validated for emptiness.

    Args:
        message (dict[str, Any]): Kafka message payload (deserialized)
            containing event identifier

    Returns:
        str: The cleaned and validated event_id string

    Raises:
        ValueError: If message is missing event identifier or the value
            is empty after stripping
    """
    raw_event_id = message.get("eventId") or message.get("event_id")
    if raw_event_id is None:
        msg = "message must include eventId or event_id"
        raise ValueError(msg)
    event_id = str(raw_event_id).strip()
    if not event_id:
        msg = "eventId must not be empty"
        raise ValueError(msg)
    return event_id
