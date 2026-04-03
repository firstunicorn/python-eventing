"""Consumer test doubles for processed-message integration tests."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from eventing.infrastructure.messaging import IdempotentConsumerBase
from eventing.infrastructure.persistence import SqlAlchemyProcessedMessageStore


class RecordingConsumer(IdempotentConsumerBase):
    """Consumer that records handled messages after durable claims succeed."""

    def __init__(self, consumer_name: str, session: AsyncSession) -> None:
        super().__init__(
            consumer_name=consumer_name,
            processed_message_store=SqlAlchemyProcessedMessageStore(session),
        )
        self.handled: list[dict[str, Any]] = []

    async def handle_event(self, message: dict[str, Any]) -> None:
        self.handled.append(message)


class FailingConsumer(IdempotentConsumerBase):
    """Consumer that fails after claiming an event identifier."""

    def __init__(self, consumer_name: str, session: AsyncSession) -> None:
        super().__init__(
            consumer_name=consumer_name,
            processed_message_store=SqlAlchemyProcessedMessageStore(session),
        )

    async def handle_event(self, message: dict[str, Any]) -> None:
        _ = message
        msg = "boom"
        raise RuntimeError(msg)
