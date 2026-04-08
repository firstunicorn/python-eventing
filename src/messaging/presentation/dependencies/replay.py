"""Dependency injection for replay service."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from messaging.infrastructure.outbox.outbox_replay import OutboxReplayService
from messaging.infrastructure.outbox.outbox_replay_queries import (
    OutboxReplayQueries,
)
from messaging.infrastructure.persistence.dependencies import get_session
from messaging.infrastructure.pubsub.kafka_publisher import KafkaEventPublisher


async def get_replay_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[OutboxReplayService]:
    """Provide replay service with dependencies."""
    queries = OutboxReplayQueries(session)
    broker = request.app.state.broker
    publisher = KafkaEventPublisher(broker)
    service = OutboxReplayService(queries, publisher)
    yield service


ReplayServiceDep = Annotated[OutboxReplayService, Depends(get_replay_service)]
