"""Shared test fixtures for infrastructure tests."""

from __future__ import annotations

from uuid import UUID

from messaging.core.contracts import BaseEvent
from python_outbox_core import IOutboxEvent


class ExampleEvent(BaseEvent):  # pylint: disable=too-many-ancestors
    """Concrete test event for infrastructure behavior."""

    event_type: str = "gamification.XPAwarded"
    aggregate_id: str = "user-123"
    source: str = "gamification-service"
    xp_delta: int


class FakeRepository:
    """Minimal async repository fake for worker and health tests."""

    def __init__(self) -> None:
        self.added: list[IOutboxEvent] = []
        self.unpublished: list[IOutboxEvent] = []
        self.published: list[UUID] = []
        self.failed: list[tuple[UUID, str]] = []
        self.pending_count = 0
        self.oldest_age = 0.0
        self.pinged = False

    async def add_event(self, event: IOutboxEvent) -> None:
        self.added.append(event)

    async def get_unpublished(self, limit: int = 100, offset: int = 0) -> list[IOutboxEvent]:
        return self.unpublished[offset : offset + limit]

    async def mark_published(self, event_id: UUID) -> None:
        self.published.append(event_id)

    async def count_unpublished(self) -> int:
        return self.pending_count

    async def mark_failed(self, event_id: UUID, error_message: str) -> None:
        self.failed.append((event_id, error_message))

    async def ping(self) -> bool:
        self.pinged = True
        return True

    async def oldest_unpublished_age_seconds(self) -> float:
        return self.oldest_age


class FakePublisher:
    """Publisher fake with configurable failure mode."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.messages: list[dict[str, object]] = []
        self.topics: list[str] = []

    async def publish(self, message: dict[str, object]) -> None:
        if self.should_fail:
            msg = "publish failed"
            raise RuntimeError(msg)
        self.messages.append(message)
        topic = str(message.get("eventType") or message.get("event_type") or "domain-events")
        self.topics.append(topic)

    async def publish_to_topic(self, topic: str, message: dict[str, object]) -> None:
        self.topics.append(topic)
        self.messages.append(message)


class FakeBroker:
    """Broker fake for health check testing."""

    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy

    async def ping(self, timeout: float | None) -> bool:
        return self.healthy and timeout == 1.0


class FakeKafkaBroker:
    """Broker fake that records publish arguments."""

    def __init__(self) -> None:
        self.published: list[tuple[dict[str, object], str, bytes | None]] = []

    async def publish(
        self,
        message: dict[str, object],
        *,
        topic: str,
        key: bytes | None,
    ) -> None:
        self.published.append((message, topic, key))
