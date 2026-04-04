"""Configuration dataclass for Kafka dead-letter handler.

Defines Kafka-specific DLQ options like header inclusion and partition key
preservation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KafkaDLQConfig:
    """Kafka-specific dead-letter handler configuration.

    Attributes
    ----------
    include_headers : bool
        Whether to add Kafka headers with error metadata (default: True).
        Headers include x-dlq-reason, x-dlq-retry-count,
        x-dlq-original-event-type, and x-dlq-routed-at.
    preserve_partition_key : bool
        Whether to use the same partition key as the original event
        (default: True). This maintains event ordering in the DLQ topic.
    """
    include_headers: bool = True
    preserve_partition_key: bool = True
