"""Execution logic for Kafka dead-letter handler.

Pure async function that orchestrates the DLQ pipeline: marking failures,
building messages with Kafka-specific headers, and publishing to the DLQ topic.
Extracted from the handler class to keep the class focused on coordination
logging.
"""

from __future__ import annotations

from typing import Any


async def execute_dlq(
    repository: Any,
    publisher: Any,
    helpers: Any,
    event: Any,
    error_message: str,
    *,
    retry_count: int = 0,
    original_topic: str | None = None,
    include_headers: bool = True,
) -> None:
    """Mark event as failed, build DLQ message, and publish to Kafka DLQ.

    Parameters
    ----------
    repository : Any
        IOutboxRepository implementation for marking events as failed
    publisher : Any
        KafkaEventPublisher that sends events to Kafka DLQ topics
    helpers : Any
        Helper module providing build_dlq_message and build_kafka_headers
    event : Any
        BaseEvent - the domain event that failed to publish
    error_message : str
        Description of the failure reason
    retry_count : int, optional
        Number of retry attempts before DLQ routing (default: 0)
    original_topic : str | None, optional
        The original topic where the event should have been published
    include_headers : bool, optional
        Whether to add Kafka headers with error metadata (default: True)
    """
    # Mark event as failed in repository
    await repository.mark_failed(event.event_id, error_message)

    # Build DLQ message with event and error context
    dlq_topic = f"{event.event_type}.DLQ"
    message = helpers.build_dlq_message(
        event,
        error_message,
        retry_count=retry_count,
        original_topic=original_topic,
    )

    # Kafka-specific: Add headers for debugging and monitoring
    if include_headers:
        headers = helpers.build_kafka_headers(
            event,
            error_message,
            retry_count=retry_count,
            original_topic=original_topic,
        )
        # Note: Headers would be passed to broker.publish() if KafkaBroker supported them
        # For now, include in message body
        message["_kafka_headers"] = headers

    # Publish to DLQ topic
    await publisher.publish_to_topic(dlq_topic, message)
