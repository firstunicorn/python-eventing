# EventBus Usage Guide

**[Overview](#overview)** • **[Architecture](#architecture)** • **[Quick Start](#quick-start)** • **[Use Cases](#use-cases)** • **[API Reference](#api-reference)**

---

## Overview

The **EventBus** is an **optional** in-process domain event dispatcher that provides an abstraction layer over the transactional outbox pattern. 

### When EventBus is NOT Needed

Most services can use the **direct outbox approach** (simpler, recommended):

```python
# Direct approach (PRIMARY pattern)
await outbox_repo.add_event(event, session=session)
await session.commit()
```

### When EventBus Adds Value

EventBus is useful when you need:

- ✅ **Multiple side effects per event** - One event triggers many handlers
- ✅ **Lifecycle hooks** - Observe/log all event dispatches
- ✅ **Testing isolation** - Enable/disable toggle for unit tests
- ✅ **Decorator syntax** - Clean `@bus.subscriber(EventType)` registration
- ✅ **Decoupled architecture** - Service layer doesn't know about outbox

If you only need to persist events to the outbox, **skip EventBus** and use direct `outbox_repo.add_event()`.

---

## Architecture

### The Central Flow (Without EventBus)

```
Service Layer
     ↓
await outbox_repo.add_event(event, session=session)  ← DIRECT
     ↓
Outbox Table (transactional)
     ↓
Outbox Worker (background)
     ↓
Kafka Publisher → External broker
```

### With EventBus (Optional Abstraction Layer)

```
Service Layer
     ↓
await event_bus.dispatch(event)  ← OPTIONAL
     ↓
EventBus (in-process dispatcher)
     ├→ OutboxEventHandler → outbox_repo.add_event()
     ├→ AuditLogHandler → audit_service.log()
     ├→ MetricsHandler → prometheus.increment()
     └→ CacheInvalidator → redis.delete()
     
Outbox Worker (background)
     ↓
Kafka Publisher → External broker
```

**Key Insight**: EventBus doesn't replace the outbox - it's a **dispatcher** that can route to multiple handlers, including the outbox.

---

## Quick Start

### Option 1: Direct Outbox (Recommended for Simple Cases)

```python
from fastapi import Depends
from messaging.core import BaseEvent
from messaging.infrastructure import SqlAlchemyOutboxRepository

class UserCreated(BaseEvent):
    event_type: str = "user.created"
    aggregate_id: str
    user_id: int

@router.post("/users")
async def create_user(
    data: CreateUserRequest,
    session = Depends(get_session),
    outbox_repo: SqlAlchemyOutboxRepository = Depends(get_outbox_repo)
):
    # Business logic
    user_id = await users_service.create_user(data, session)
    
    # Persist event to outbox (same transaction)
    await outbox_repo.add_event(
        UserCreated(aggregate_id=f"user-{user_id}", user_id=user_id),
        session=session
    )
    
    await session.commit()  # Atomic: user + event
    return {"user_id": user_id}
```

### Option 2: With EventBus (For Multiple Handlers)

```python
from fastapi import Request
from messaging.infrastructure import OutboxEventHandler

@router.post("/users")
async def create_user(data: CreateUserRequest, request: Request):
    event_bus = request.app.state.event_bus
    outbox_repo = request.app.state.outbox_repository
    
    # Register multiple handlers
    event_bus.register(UserCreated, OutboxEventHandler(outbox_repo))
    event_bus.register(UserCreated, AuditLogHandler())
    event_bus.register(UserCreated, MetricsHandler())
    
    # Business logic
    user_id = await users_service.create_user(data)
    
    # Dispatch → all handlers execute
    await event_bus.dispatch(UserCreated(
        aggregate_id=f"user-{user_id}",
        user_id=user_id,
    ))
    
    return {"user_id": user_id}
```

**When to use which**:
- **Direct outbox**: Single destination (just Kafka), simple
- **EventBus**: Multiple side effects, hooks, testing isolation

---

## Use Cases

### Use Case 1: Transactional Outbox Pattern

**Problem**: Ensure domain events are reliably published to Kafka, even if the service crashes.

**Solution**: EventBus dispatches to `OutboxEventHandler`, which persists events in the same database transaction as business data.

```python
from messaging.infrastructure import OutboxEventHandler

# In service layer
async def create_order(data, session):
    # 1. Business logic
    order = Order(**data)
    session.add(order)

    # 2. Register outbox handler
    event_bus.register(OrderPlaced, OutboxEventHandler(outbox_repository))

    # 3. Dispatch event (persisted in outbox table)
    await event_bus.dispatch(OrderPlaced(
        aggregate_id=f"order-{order.id}",
        order_id=order.id,
        customer_id=order.customer_id,
    ))

    # 4. Commit both order + outbox event atomically
    await session.commit()

    # 5. Outbox worker publishes to Kafka asynchronously
```

**Result**: Atomic writes, guaranteed delivery, no lost events.

---

### Use Case 2: Multiple Side Effects per Event

**Problem**: One business action triggers multiple side effects (audit, metrics, cache, notifications).

**Solution**: Register multiple handlers for the same event type.

```python
# Multiple handlers for OrderPlaced event
event_bus.register(OrderPlaced, OutboxEventHandler(outbox_repo))       # Kafka
event_bus.register(OrderPlaced, AuditLogHandler(audit_service))        # Audit
event_bus.register(OrderPlaced, MetricsHandler(prometheus_registry))   # Metrics
event_bus.register(OrderPlaced, CacheInvalidator(redis_client))        # Cache

# One dispatch → all handlers execute
await event_bus.dispatch(OrderPlaced(...))
```

**Result**: Decoupled side effects, clean service layer code, easy to add/remove handlers.

---

### Use Case 3: Observability with Lifecycle Hooks

**Problem**: Need visibility into all domain event flows for debugging and monitoring.

**Solution**: Use lifecycle hooks to log/trace all dispatches.

```python
from messaging.core import DispatchHooks

def log_dispatch(trace):
    logger.info(
        "Event dispatched",
        event_type=trace.event.event_type,
        handler=trace.handler_name,
        backend=trace.backend_name,
    )

def log_failure(trace):
    logger.error(
        "Handler failed",
        event_type=trace.event.event_type,
        handler=trace.handler_name,
        error=str(trace.error),
    )

def update_metrics(trace):
    metrics.increment(
        "event_bus.handler.success",
        tags={"event_type": trace.event.event_type}
    )

# Wire hooks at startup
event_bus = build_event_bus(
    [],
    hooks=DispatchHooks(
        on_dispatch=log_dispatch,
        on_success=update_metrics,
        on_failure=log_failure,
    )
)
```

**Result**: Full observability of event flows, structured logs, Prometheus metrics.

---

### Use Case 4: Testing with Enable/Disable Toggle

**Problem**: Unit tests trigger real side effects (database writes, external calls).

**Solution**: Disable EventBus in tests to isolate business logic.

```python
# Production: events dispatched normally
event_bus = EventBus(settings=DispatchSettings(enabled=True))

# Unit tests: disable side effects
event_bus = EventBus(settings=DispatchSettings(enabled=False))

# Test service logic without triggering handlers
await service.create_user(data)  # EventBus disabled, no DB writes
```

**Result**: Fast, isolated unit tests without mocking.

---

### Use Case 5: Custom Dispatch Strategies

**Problem**: Need parallel execution of independent handlers for performance.

**Solution**: Implement custom `DispatchBackend`.

```python
from messaging.core import DispatchBackend
import asyncio

class ParallelDispatchBackend(DispatchBackend):
    name = "parallel"

    async def invoke(self, event, handlers, invoke_one):
        # Execute all handlers concurrently
        await asyncio.gather(*[
            invoke_one(handler) for handler in handlers
        ])

# Use custom backend
event_bus = EventBus(backend=ParallelDispatchBackend())
```

**Result**: Concurrent handler execution for performance-critical paths.

---

### Use Case 6: Domain Event Sourcing (Saga Orchestration)

**Problem**: Coordinate multi-step business processes across aggregates.

**Solution**: Use EventBus to trigger saga steps based on domain events.

```python
# Saga coordinator listens to domain events
@event_bus.subscriber(OrderPlaced)
async def start_order_saga(event: OrderPlaced):
    await saga_service.reserve_inventory(event.order_id)

@event_bus.subscriber(InventoryReserved)
async def process_payment(event: InventoryReserved):
    await payment_service.charge(event.order_id)

@event_bus.subscriber(PaymentSucceeded)
async def fulfill_order(event: PaymentSucceeded):
    await fulfillment_service.ship(event.order_id)
```

**Result**: Decoupled saga orchestration without tight coupling between services.

---

## API Reference

### EventBus

```python
class EventBus:
    def __init__(
        self,
        *,
        backend: DispatchBackend | None = None,      # Default: SequentialDispatchBackend()
        hooks: DispatchHooks | None = None,          # Optional lifecycle hooks
        settings: DispatchSettings | None = None,    # Optional config (enabled, debug)
    ) -> None: ...

    def register(
        self,
        event_type: type[BaseEvent],
        handler: IDomainEventHandler | Callable,     # Handler instance or async callback
        *,
        handler_name: str | None = None,             # Optional name for tracing
    ) -> None:
        """Register a handler for an event type."""

    def subscriber(
        self,
        event_type: type[BaseEvent],
        *,
        handler_name: str | None = None,
    ) -> Callable:
        """Decorator for registering async callbacks."""

    async def dispatch(self, event: BaseEvent) -> None:
        """Dispatch event to all registered handlers."""
```

### DispatchHooks

```python
@dataclass(frozen=True)
class DispatchHooks:
    on_dispatch: Callable[[DispatchTrace], None] | None = None   # Before dispatch
    on_success: Callable[[DispatchTrace], None] | None = None    # After success
    on_failure: Callable[[DispatchTrace], None] | None = None    # After failure
    on_disabled: Callable[[DispatchTrace], None] | None = None   # When disabled
    on_debug: Callable[[DispatchTrace], None] | None = None      # Debug tracing
```

### DispatchTrace

```python
@dataclass(frozen=True)
class DispatchTrace:
    stage: str              # "dispatch", "success", "failure", "disabled"
    event: BaseEvent        # The dispatched event
    backend_name: str       # Backend identifier ("sequential", "parallel", etc.)
    handler_name: str | None = None  # Handler being invoked
    error: Exception | None = None   # Exception if failure
```

### DispatchSettings

```python
@dataclass(frozen=True)
class DispatchSettings:
    enabled: bool = True    # If False, dispatch is skipped
    debug: bool = False     # If True, on_debug hook is emitted
```

---

## Best Practices

### 1. Register Handlers at Startup (Not Per-Request)

❌ **Bad** - Registers handler on every request:
```python
@router.post("/users")
async def create_user(request: Request):
    event_bus = request.app.state.event_bus
    event_bus.register(UserCreated, OutboxEventHandler(repo))  # Re-registers every time!
    await event_bus.dispatch(UserCreated(...))
```

✅ **Good** - Register once at startup or module-level:
```python
# In startup lifespan or module init
event_bus.register(UserCreated, OutboxEventHandler(outbox_repository))

# In handlers, just dispatch
@router.post("/users")
async def create_user(request: Request):
    await request.app.state.event_bus.dispatch(UserCreated(...))
```

---

### 2. Use Specific Event Types (Not Generic Events)

❌ **Bad** - Generic "something changed" events:
```python
await event_bus.dispatch(GenericEvent(data={"user_id": 123}))
```

✅ **Good** - Explicit, typed domain events:
```python
class UserCreated(BaseEvent):
    event_type: str = "user.created"
    aggregate_id: str
    user_id: int
    email: str

await event_bus.dispatch(UserCreated(
    aggregate_id=f"user-{user_id}",
    user_id=user_id,
    email=email,
))
```

---

### 3. Keep Handlers Idempotent

Handlers may be retried, so ensure they're safe to execute multiple times:

```python
class AuditLogHandler(IDomainEventHandler[OrderPlaced]):
    async def handle(self, event: OrderPlaced):
        # Use event ID to prevent duplicate logs
        if not await audit_repo.exists(event.id):
            await audit_repo.create(event)
```

---

### 4. Use Lifecycle Hooks for Cross-Cutting Concerns

Don't pollute handlers with logging/metrics - use hooks instead:

❌ **Bad**:
```python
async def handle(self, event: UserCreated):
    logger.info(f"Handling {event.event_type}")  # Repeated in every handler
    await do_work(event)
    logger.info("Success")
```

✅ **Good**:
```python
# Hooks configured once at startup
event_bus = EventBus(
    hooks=DispatchHooks(
        on_dispatch=lambda trace: logger.info(f"Handling {trace.event.event_type}"),
        on_success=lambda trace: logger.info(f"Success: {trace.handler_name}"),
    )
)

# Handlers stay clean
async def handle(self, event: UserCreated):
    await do_work(event)  # No logging noise
```

---

### 5. Separate Domain Events from Integration Events

- **Domain events** (EventBus): Internal to the service, in-process
- **Integration events** (Kafka): Cross-service, asynchronous

```python
# Domain event (EventBus)
class OrderPlaced(BaseEvent):
    event_type: str = "order.placed"
    order_id: int
    customer_id: int

# Integration event (Kafka - published from outbox)
# Same schema, but goes through outbox → Kafka
```

---

## When NOT to Use EventBus

EventBus is **not** for:

1. ❌ **Cross-service communication** - Use Kafka/RabbitMQ
2. ❌ **External API calls** - Use direct HTTP clients
3. ❌ **Long-running background jobs** - Use task queue (Celery, etc.)
4. ❌ **Request/response patterns** - Use CQRS mediator pattern

EventBus is **for**:

1. ✅ **In-process side effects** - Multiple handlers per event
2. ✅ **Domain event dispatch** - Transactional outbox pattern
3. ✅ **Decoupled business logic** - Service → EventBus → Handlers
4. ✅ **Testing isolation** - Enable/disable toggle

---

## EventBus vs Direct Outbox: When to Use Which

EventBus is **optional** - the direct outbox pattern is often simpler and clearer.

### Direct Outbox (Recommended for most cases)

```python
async def create_user(data, session, outbox_repo):
    user = User(**data)
    session.add(user)
    
    # Direct, simple, clear
    await outbox_repo.add_event(
        UserCreated(user_id=user.id),
        session=session
    )
    
    await session.commit()
```

**Use when**:
- ✅ Single destination (just outbox → Kafka)
- ✅ Simple, straightforward flow
- ✅ No need for multiple side effects

### EventBus (For complex scenarios)

```python
async def create_user(data, session, event_bus):
    user = User(**data)
    session.add(user)
    
    # Decoupled, flexible, multiple handlers
    await event_bus.dispatch(UserCreated(user_id=user.id))
    
    await session.commit()
```

**Use when**:
- ✅ Multiple side effects per event (outbox + audit + metrics + cache)
- ✅ Need lifecycle hooks for observability
- ✅ Testing isolation (enable/disable toggle)
- ✅ Decorator-based handler registration preferred

**EventBus Benefits**:
- Multiple handlers per event
- Service layer doesn't import infrastructure
- Easy to add/remove handlers
- Testable without mocking

**EventBus Drawbacks**:
- Extra abstraction layer (more complexity)
- Must wire up EventBus and register handlers
- Overkill for simple event persistence

---

## Troubleshooting

### Handler Not Executing

1. Check registration: `event_bus._handlers` should contain your event type
2. Verify dispatch is called: Add `on_dispatch` hook
3. Check `enabled` setting: `DispatchSettings(enabled=True)`

### Events Not Persisting to Outbox

1. Verify `OutboxEventHandler` is registered
2. Check session commit happens after dispatch
3. Verify outbox worker is running (`settings.outbox_worker_enabled=True`)

### Performance Issues

1. Use `ParallelDispatchBackend` for independent handlers
2. Profile handlers with `on_success` hook timing
3. Consider async handlers with proper `await`

---

## Examples

See [`tests/unit/core/test_event_bus.py`](../../tests/unit/core/test_event_bus.py) for comprehensive examples of all features.
