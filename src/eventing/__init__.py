"""Universal event infrastructure for microservices.

This package provides reusable event contracts, transactional outbox publishing,
Kafka integration, and in-process dispatch patterns for event-driven architectures.

Key Components
--------------
- eventing.core : Event definitions, registry, and envelope formatting
- eventing.infrastructure : Outbox, messaging, and persistence implementations

Quick Start
-----------
>>> from eventing.core import BaseEvent, EventBus, build_event_bus
>>> from eventing.infrastructure import OutboxEventHandler
>>>
>>> # Define events
>>> class UserCreated(BaseEvent):
...     event_type: str = "user.created"
...     user_id: int
>>>
>>> # Set up event bus with outbox
>>> event_bus = build_event_bus()
>>> event_bus.register(UserCreated, OutboxEventHandler(session))
"""
