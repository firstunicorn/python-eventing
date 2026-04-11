from typing import Any, Generic, TypeVar

from pydantic import BaseModel

TEvent = TypeVar("TEvent")

class BaseDomainEvent(BaseModel):
    pass

class IDomainEventHandler(Generic[TEvent]):
    async def handle(self, event: TEvent) -> None: ...

class InProcessEventDispatcher:
    def __init__(self) -> None: ...
    def register(self, event_type: type[Any], handler: IDomainEventHandler[Any]) -> None: ...
    async def dispatch(self, event: Any) -> None: ...
