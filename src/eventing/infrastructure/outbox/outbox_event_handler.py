"""In-process handler that writes domain events to the transactional outbox."""

from eventing.core.contracts import BaseEvent
from python_domain_events import IDomainEventHandler
from python_outbox_core import IOutboxRepository


class OutboxEventHandler(IDomainEventHandler[BaseEvent]):
    """Persist dispatched domain events into the outbox."""

    def __init__(self, repository: IOutboxRepository) -> None:
        self._repository = repository

    async def handle(self, event: BaseEvent) -> None:
        """Store the event in the outbox repository."""
        await self._repository.add_event(event)
