"""In-process handler that writes domain events to the transactional outbox.

This module provides the `OutboxEventHandler` which acts as a bridge between
the in-process `EventBus` and the persistent `SqlAlchemyOutboxRepository`.
When registered as a subscriber, it automatically persists any emitted events.

See Also
--------
- messaging.core.contracts.bus.event_bus : The event bus where this handler is registered
"""

from messaging.core.contracts import BaseEvent
from python_domain_events import IDomainEventHandler
from python_outbox_core import IOutboxRepository


class OutboxEventHandler(IDomainEventHandler[BaseEvent]):
    """Persist dispatched domain events into the outbox."""

    def __init__(self, repository: IOutboxRepository) -> None:
        self._repository = repository

    async def handle(self, event: BaseEvent) -> None:
        """Store the event in the outbox repository."""
        await self._repository.add_event(event)
