"""Event replay service for querying and republishing events."""

from datetime import datetime

from python_outbox_core.events import IOutboxEvent

from messaging.infrastructure.outbox.outbox_replay_queries import (
    OutboxReplayQueries,
)
from messaging.infrastructure.pubsub.kafka_publisher import KafkaEventPublisher


class OutboxReplayService:
    """Query and replay outbox events by type and time range."""

    def __init__(
        self,
        queries: OutboxReplayQueries,
        publisher: KafkaEventPublisher,
    ) -> None:
        """Initialize with queries and publisher."""
        self._queries = queries
        self._publisher = publisher

    async def query(  # type: ignore[no-any-unimported]
        self,
        event_type: str | None,
        from_ts: datetime,
        to_ts: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IOutboxEvent]:
        """Query events matching criteria without republishing."""
        return await self._queries.get_by_type_and_range(
            event_type=event_type,
            from_ts=from_ts,
            to_ts=to_ts,
            limit=limit,
            offset=offset,
        )

    async def replay(
        self,
        event_type: str | None,
        from_ts: datetime,
        to_ts: datetime,
        limit: int = 1000,
    ) -> int:
        """Replay events matching criteria by republishing to Kafka.

        Returns:
            Number of events republished
        """
        events = await self._queries.get_by_type_and_range(
            event_type=event_type,
            from_ts=from_ts,
            to_ts=to_ts,
            limit=limit,
            offset=0,
        )

        replayed_count = 0
        for event in events:
            message = event.to_message()
            await self._publisher.publish(message)
            replayed_count += 1

        return replayed_count
