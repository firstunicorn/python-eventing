"""Event ID and error reason extraction from DLQ messages.

Pure functions for extracting event identifiers and error metadata from
native DLQ messages (RabbitMQ DLX, Kafka Connect DLQ SMT).
"""

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def extract_event_id(msg: dict[str, Any]) -> UUID:
    """Extract event_id from DLQ message payload or headers.

    Args:
        msg: The DLQ message payload

    Returns:
        UUID: The event identifier

    Raises:
        ValueError: If event_id cannot be extracted
    """
    # Try direct payload fields (both camelCase and snake_case)
    event_id_str = msg.get("eventId") or msg.get("event_id")
    if event_id_str:
        return UUID(event_id_str)

    # Try nested event object (DLQ wrapper format)
    event = msg.get("event", {})
    event_id_str = event.get("eventId") or event.get("event_id")
    if event_id_str:
        return UUID(event_id_str)

    error_msg = "Cannot extract event_id from DLQ message"
    logger.error("%s: %s", error_msg, msg)
    raise ValueError(error_msg)


def extract_error_reason(msg: dict[str, Any], headers: dict[str, Any]) -> str:
    """Extract error reason from DLQ message or headers.

    Args:
        msg: The DLQ message payload
        headers: Message headers

    Returns:
        str: The error reason/description
    """
    # Try RabbitMQ x-death header
    x_death = headers.get("x-death", [])
    if x_death and isinstance(x_death, list) and len(x_death) > 0:
        reason = x_death[0].get("reason")
        if reason:
            return str(reason)

    # Try Kafka Connect error headers
    kafka_error = headers.get("kafka.connect.error.message")
    if kafka_error:
        return str(kafka_error)

    # Try direct message error field
    error = msg.get("error")
    if error:
        return str(error)

    return "Unknown error (DLQ)"
