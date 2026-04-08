"""Dead letter handler for Kafka failed messages (placeholder)."""

from sqlalchemy.ext.asyncio import AsyncSession


class KafkaDeadLetterHandler:
    """Handle dead-lettered Kafka messages."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize dead letter handler."""
        self._session = session
