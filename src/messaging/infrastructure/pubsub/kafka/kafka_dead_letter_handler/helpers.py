"""Helper functions for Kafka DLQ message construction.

Pure functions for building DLQ messages and Kafka headers with error metadata.
Extracted from KafkaDeadLetterHandler to keep the handler class focused on
orchestration while message-building logic remains pure and testable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from messaging.core.contracts import BaseEvent


def build_dlq_message(
    event: BaseEvent,
    error_message: str,
    *,
    retry_count: int = 0,
    original_topic: str | None = None,
) -> dict[str, Any]:
    """Build DLQ message payload with event and error context.

    Parameters
    ----------
    event : BaseEvent
        The domain event that failed to publish
    error_message : str
        Description of the failure reason
    retry_count : int, optional
        Number of retry attempts before DLQ routing (default: 0)
    original_topic : str | None, optional
        The original topic where the event should have been published

    Returns
    -------
    dict[str, Any]
        DLQ message with event data, error info, and optional original_topic
    """
    message = {
        "event": event.to_message(),
        "error": error_message,
        "dlq_routed_at": datetime.now(UTC).isoformat(),
        "retry_count": retry_count,
    }
    if original_topic:
        message["original_topic"] = original_topic
    return message


def build_kafka_headers(
    event: BaseEvent,
    error_message: str,
    *,
    retry_count: int = 0,
    original_topic: str | None = None,
) -> dict[str, str]:
    """Build Kafka headers for DLQ messages with error metadata.

    Parameters
    ----------
    event : BaseEvent
        The domain event being routed to DLQ
    error_message : str
        Description of the failure reason
    retry_count : int, optional
        Number of retry attempts before DLQ routing (default: 0)
    original_topic : str | None, optional
        The original topic where the event should have been published

    Returns
    -------
    dict[str, str]
        Kafka headers for error tracking and monitoring
    """
    headers = {
        "x-dlq-reason": error_message,
        "x-dlq-retry-count": str(retry_count),
        "x-dlq-original-event-type": event.event_type,
        "x-dlq-routed-at": datetime.now(UTC).isoformat(),
    }
    if original_topic:
        headers["x-dlq-original-topic"] = original_topic
    return headers
