# File Size Refactoring Plan

## Overview

This document outlines the strategy for splitting files exceeding the 100-line limit (target: ≤75 lines per file).

## Priority 1: event_bus.py (101 lines) → 4 files

**Current violations**: File size (101 lines) + SRP (mixes handler resolution, execution, hooks)

**Target structure**:

### 1. `handler_resolver.py` (~20 lines)
```python
"""Handler name resolution for event bus registrations."""

class HandlerResolver:
    """Resolve handler names from handler instances or callbacks."""

    @staticmethod
    def resolve_name(handler: HandlerLike) -> str:
        """Extract handler name from class or function."""
        if hasattr(handler, "handle"):
            return handler.__class__.__name__
        return handler.__name__

    @staticmethod
    def extract_callback(handler: HandlerLike) -> EventCallback:
        """Extract callable from handler instance or return callback directly."""
        return handler.handle if hasattr(handler, "handle") else handler
```

### 2. `dispatch_executor.py` (~35 lines)
```python
"""Handler invocation and error handling for event dispatch."""

class DispatchExecutor:
    """Execute handlers with tracing and error handling."""

    def __init__(self, hooks: DispatchHooks, backend_name: str) -> None:
        self._hooks = hooks
        self._backend_name = backend_name

    async def invoke_handler(
        self,
        event: BaseEvent,
        handler: RegisteredHandler,
    ) -> None:
        """Invoke one handler with tracing and error handling."""
        dispatch_trace = DispatchTrace("dispatch", event, self._backend_name, handler.name)
        self._hooks.emit("on_dispatch", dispatch_trace)

        try:
            await handler.callback(event)
        except Exception as error:
            self._hooks.emit(
                "on_failure",
                DispatchTrace("failure", event, self._backend_name, handler.name, error),
            )
            raise

        self._hooks.emit(
            "on_success",
            DispatchTrace("success", event, self._backend_name, handler.name),
        )
```

### 3. `hook_emitter.py` (~25 lines)
```python
"""Hook emission logic for event bus lifecycle."""

class HookEmitter:
    """Emit lifecycle hooks with debug support."""

    def __init__(self, hooks: DispatchHooks, settings: DispatchSettings) -> None:
        self._hooks = hooks
        self._settings = settings

    def emit(self, attribute: str, trace: DispatchTrace) -> None:
        """Emit a specific hook with optional debug tracing."""
        hook = getattr(self._hooks, attribute)
        if hook is not None:
            hook(trace)
        if self._settings.debug and self._hooks.on_debug is not None:
            self._hooks.on_debug(trace)
```

### 4. `event_bus.py` (~35 lines) - Thin coordinator
```python
"""Decorator-friendly facade for in-process event dispatch."""

class EventBus:
    """Provide a higher-level event emitter/subscriber facade."""

    def __init__(
        self,
        *,
        backend: DispatchBackend | None = None,
        hooks: DispatchHooks | None = None,
        settings: DispatchSettings | None = None,
    ) -> None:
        self._backend = backend or SequentialDispatchBackend()
        self._hooks_emitter = HookEmitter(hooks or DispatchHooks(), settings or DispatchSettings())
        self._executor = DispatchExecutor(hooks or DispatchHooks(), self._backend.name)
        self._resolver = HandlerResolver()
        self._settings = settings or DispatchSettings()
        self._handlers: dict[type[BaseEvent], list[RegisteredHandler]] = {}

    def register(
        self,
        event_type: type[BaseEvent],
        handler: HandlerLike,
        *,
        handler_name: str | None = None,
    ) -> None:
        """Register one handler instance or async callback."""
        callback = self._resolver.extract_callback(handler)
        name = handler_name or self._resolver.resolve_name(handler)
        self._handlers.setdefault(event_type, []).append(RegisteredHandler(name, callback))

    def subscriber(
        self,
        event_type: type[BaseEvent],
        *,
        handler_name: str | None = None,
    ) -> Callable[[EventCallback], EventCallback]:
        """Register an async callback through a decorator."""
        # Implementation delegates to register()

    async def dispatch(self, event: BaseEvent) -> None:
        """Dispatch one event through the configured backend."""
        # Implementation uses _executor and _hooks_emitter
```

**Benefits**:
- Each file ≤35 lines (well under 75-line target)
- Single Responsibility: Each class has one clear purpose
- Easier to test each component in isolation
- Maintains public API (EventBus public API unchanged)

---

## Priority 2: outbox_repository.py (119 lines) → 3 files

**Current violations**: File size (119 lines)

**Target structure**:

### 1. `outbox_crud.py` (~45 lines)
```python
"""Core CRUD operations for outbox events."""

class OutboxCrudOperations:
    """Handle basic create and update operations for outbox events."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: EventRegistry,
    ) -> None:
        self._session_factory = session_factory
        self._registry = registry

    async def add_event(self, event: IOutboxEvent, session: AsyncSession | None = None) -> None:
        """Store a serialized event in the provided or new session."""
        # Implementation with session parameter for transactional outbox

    async def mark_published(self, event_id: UUID) -> None:
        """Mark an event as published and timestamp the update."""

    async def mark_failed(self, event_id: UUID, error_message: str) -> None:
        """Persist failure state and error details for an event."""

    async def _mark(self, event_id: str, **values: object) -> None:
        """Generic update helper for status changes."""

    @staticmethod
    def _to_record(event: IOutboxEvent) -> OutboxEventRecord:
        """Convert domain event to ORM record."""
```

### 2. `outbox_queries.py` (~40 lines)
```python
"""Query operations for outbox event status and metrics."""

class OutboxQueryOperations:
    """Handle read-only queries for outbox status."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], registry: EventRegistry) -> None:
        self._session_factory = session_factory
        self._registry = registry

    async def get_unpublished(self, limit: int = 100, offset: int = 0) -> list[IOutboxEvent]:
        """Fetch unpublished events ordered by creation time."""

    async def count_unpublished(self) -> int:
        """Count pending unpublished and non-failed events."""

    async def oldest_unpublished_age_seconds(self) -> float:
        """Return the age of the oldest pending event in seconds."""

    async def ping(self) -> bool:
        """Check if the backing database is reachable."""
```

### 3. `outbox_repository.py` (~35 lines) - Facade
```python
"""SQLAlchemy implementation of the outbox repository contract."""

class SqlAlchemyOutboxRepository(IOutboxRepository):
    """Persist and retrieve outbox events with SQLAlchemy async sessions."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: EventRegistry,
    ) -> None:
        self._crud = OutboxCrudOperations(session_factory, registry)
        self._queries = OutboxQueryOperations(session_factory, registry)

    # Delegate all methods to _crud and _queries
    async def add_event(self, event: IOutboxEvent, session: AsyncSession | None = None) -> None:
        """Store a serialized event without committing the transaction."""
        await self._crud.add_event(event, session)

    # ... other delegations
```

**Benefits**:
- Each file ~35-45 lines (under 75-line target)
- Separation of Concerns: CRUD vs Queries
- Easier to add session parameter for transactional outbox (fixes violation #3)
- Maintains interface contract

---

## Priority 3: Test files

### test_outbox_infrastructure.py (210 lines) → 3 files

Split by test concern:
1. `test_outbox_crud.py` (~70 lines) - add_event, mark_published, mark_failed
2. `test_outbox_queries.py` (~70 lines) - get_unpublished, count, oldest_age
3. `test_outbox_integration.py` (~70 lines) - end-to-end flows, health checks

### test_main_and_routing.py (175 lines) → 2 files

1. `test_lifespan.py` (~90 lines) - lifespan context manager, startup/shutdown
2. `test_routing.py` (~85 lines) - API endpoints, health checks

### test_event_bus.py (167 lines) → 2 files

1. `test_event_bus_registration.py` (~85 lines) - register, subscriber, decorator
2. `test_event_bus_dispatch.py` (~82 lines) - dispatch, hooks, backends

---

## Implementation order

1. **event_bus.py** (Priority 1 - fixes both file size + SRP)
2. **outbox_repository.py** (Priority 2 - enables transactional outbox fix)
3. **Test files** (Priority 3 - after source files stabilize)

## Public API Guarantee

All refactorings maintain public API definitions:
- `EventBus` class remains importable from original location
- `SqlAlchemyOutboxRepository` interface unchanged
- Internal imports updated, external usage unaffected

## Validation

After each refactoring:
- [ ] Run full test suite
- [ ] Verify mypy passes (strict mode)
- [ ] Verify ruff/pylint pass
- [ ] Check import paths in all consuming code
- [ ] Verify line counts: `wc -l <file>` ≤75 for each new file
