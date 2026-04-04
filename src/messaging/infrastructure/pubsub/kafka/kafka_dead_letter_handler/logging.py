"""Logging functions for Kafka DLQ operations.

Provides structured logging for DLQ routing events with consistent
message formats across warning and info levels.
"""

from __future__ import annotations

import logging
from uuid import UUID

from messaging.core.contracts import BaseEvent

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def log_dlq_routing(
    event: BaseEvent,
    error_message: str,
    retry_count: int,
) -> None:
    """Log warning about routing event to DLQ.

    Parameters
    ----------
    event : BaseEvent
        The domain event being routed to DLQ
    error_message : str
        Description of the failure reason
    retry_count : int
        Number of retry attempts before DLQ routing
    """
    logger.warning(
        "Routing event %s (type=%s) to Kafka DLQ after %d retries: %s",
        event.event_id,
        event.event_type,
        retry_count,
        error_message,
    )


def log_dlq_published(
    event_id: str | UUID,
    dlq_topic: str,
    include_headers: bool,
) -> None:
    """Log info about event published to DLQ.

    Parameters
    ----------
    event_id : str | UUID
        Unique identifier of the routed event
    dlq_topic : str
        The DLQ topic where the event was published
    include_headers : bool
        Whether Kafka headers were included in the message
    """
    logger.info(
        "Event %s published to Kafka DLQ topic '%s' with headers=%s",
        event_id,
        dlq_topic,
        include_headers,
    )
