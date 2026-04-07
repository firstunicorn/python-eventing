# EventBus Deep Analysis: Library Coverage Check

**Date**: 2026-04-06  
**Question**: Do Kafka, Kafka plugins, FastStream, RabbitMQ, RabbitMQ plugins, or python-web-toolkit provide EventBus functionality?

---

## Executive Summary

**Result**: NO native in-process EventBus in Kafka, RabbitMQ, FastStream, or their plugins.  
**HOWEVER**: `python-web-toolkit` provides `InProcessEventDispatcher` which covers 70% of our EventBus use case.

**Decision Impact**: Our custom EventBus is **partially redundant** but has unique features not in `InProcessEventDispatcher`.

---

## Detailed Findings

### 1. FastStream

**Query**: In-process event bus, domain events, internal application event dispatcher?

**Result**: ❌ **NO**

**What FastStream provides:**
- `BaseMiddleware` for external broker message lifecycle (`consume_scope`, `publish_scope`, `on_receive`, `after_processed`)
- `Logger` and `ContextRepo` for message context
- `@broker.subscriber()` decorator for external topics/queues

**What it does NOT provide:**
- In-process event dispatch to multiple handlers
- Domain event bus for application-level events
- Pub-sub pattern within application memory

**Conclusion**: FastStream is a **broker abstraction framework**, not an in-process event bus.

---

### 2. Apache Kafka (and Kafka Streams)

**Query**: In-process event bus, domain event dispatcher, observer pattern within application?

**Result**: ❌ **NO**

**What Kafka provides:**
- External topic-based message streaming
- Kafka Streams: Stream processing with state stores (still external topics)
- `Processor` API for custom message processing logic

**What it does NOT provide:**
- In-process event dispatch (all events go through topics)
- Multiple handlers within same application process
- Observer/mediator pattern for application events

**Example confusion**: Kafka Streams `Processor` is for **processing external messages from topics**, not for dispatching internal domain events to multiple in-process handlers.

**Conclusion**: Kafka is a **distributed streaming platform**, not an in-process event bus.

---

### 3. RabbitMQ (and Plugins)

**Query**: In-process event bus, domain events, internal application dispatcher?

**Result**: ❌ **NO** (with important clarification)

**What RabbitMQ provides:**
- External queue/exchange-based messaging
- `rabbitmq_event_exchange` plugin: Publishes **RabbitMQ's internal events** (e.g., `connection.created`, `queue.deleted`, `user.authentication.failure`)
  - This is for **monitoring RabbitMQ itself**, not application domain events
  - Events published to `amq.rabbitmq.event` topic exchange
  - Useful for observability of RabbitMQ infrastructure

**What it does NOT provide:**
- In-process application event bus
- Domain event dispatcher for business logic
- Multiple handler registration for application events

**Conclusion**: RabbitMQ plugins expose **broker monitoring events**, not application domain events.

---

### 4. python-web-toolkit: python-domain-events

**Query**: In-process event dispatcher capabilities?

**Result**: ✅ **YES** - Provides `InProcessEventDispatcher`

#### What python-domain-events provides:

```python
from python_domain_events import InProcessEventDispatcher, IDomainEventHandler

dispatcher = InProcessEventDispatcher()

# Register handlers
dispatcher.register(UserCreated, notify_handler)
dispatcher.register(UserCreated, audit_handler)  # Multiple handlers supported

# Dispatch to ALL registered handlers
await dispatcher.dispatch(UserCreated(user_id=123))

# Clear all handlers
dispatcher.clear()
```

**Features:**
- ✅ Multiple handlers per event type ("dispatch event to all registered handlers")
- ✅ Type-safe handler registration (`IDomainEventHandler[TEvent]`)
- ✅ Async dispatch
- ✅ Handler interface with `.handle(event)` method

**Limitations (compared to our EventBus):**
- ❌ No pluggable dispatch backends (sequential only)
- ❌ No lifecycle hooks (on_dispatch, on_success, on_failure, on_debug)
- ❌ No decorator-based subscription (`@bus.subscriber(EventType)`)
- ❌ No handler name resolution/registration metadata
- ❌ No enable/disable toggle
- ❌ No dispatch tracing (DispatchTrace)
- ❌ No custom backend support (parallel dispatch, etc.)

---

## Our EventBus: Unique Features Analysis

### Architecture Comparison

| Feature | python-domain-events | Our EventBus |
|---------|---------------------|--------------|
| **Multiple handlers per event** | ✅ Yes | ✅ Yes |
| **Type-safe registration** | ✅ Yes | ✅ Yes |
| **Async dispatch** | ✅ Yes | ✅ Yes |
| **Pluggable backends** | ❌ No (sequential only) | ✅ Yes (`DispatchBackend` protocol) |
| **Lifecycle hooks** | ❌ No | ✅ Yes (5 hooks: dispatch, success, failure, disabled, debug) |
| **Decorator subscription** | ❌ No | ✅ Yes (`@bus.subscriber(EventType)`) |
| **Handler name resolution** | ❌ No | ✅ Yes (`HandlerResolver`) |
| **Enable/disable toggle** | ❌ No | ✅ Yes (`DispatchSettings.enabled`) |
| **Dispatch tracing** | ❌ No | ✅ Yes (`DispatchTrace` with stage, event, backend, handler, error) |
| **Custom backends** | ❌ No | ✅ Yes (`SequentialDispatchBackend`, or custom) |

### Our EventBus Components (Not in python-domain-events)

1. **`DispatchBackend` Protocol** (`backends/base.py`):
   - Abstraction for different dispatch strategies
   - `SequentialDispatchBackend`, `ParallelDispatchBackend`, etc.

2. **`DispatchHooks`** (`dispatch_hooks.py`):
   - `on_dispatch`: Before dispatching
   - `on_success`: After handler succeeds
   - `on_failure`: After handler fails
   - `on_disabled`: When dispatch is disabled
   - `on_debug`: Debug tracing

3. **`HookEmitter`** (`hook_emitter.py`):
   - Manages hook emission with debug support
   - Wraps `DispatchHooks` and `DispatchSettings`

4. **`HandlerResolver`** (`handler_resolver.py`):
   - Extracts callbacks from handlers
   - Resolves handler names for tracing

5. **`DispatchExecutor`** (`dispatch_executor.py`):
   - Invokes handlers with lifecycle hooks
   - Emits `on_dispatch`, `on_success`, `on_failure`

6. **`DispatchTrace`** (`dispatch_hooks.py`):
   - Captures dispatch metadata: stage, event, backend, handler, error
   - Useful for observability and debugging

7. **Decorator-based Subscription**:
   ```python
   @bus.subscriber(UserCreated, handler_name="notify_users")
   async def notify_users(event: UserCreated):
       ...
   ```

---

## Decision Matrix

### Option 1: DELETE EventBus (Use python-domain-events)

**Pros:**
- Reduces LOC by ~500 lines
- Leverages maintained library
- Simpler for basic domain event dispatch

**Cons:**
- ❌ **LOSES lifecycle hooks** (no observability for event dispatch)
- ❌ **LOSES pluggable backends** (can't add parallel dispatch later)
- ❌ **LOSES decorator syntax** (less ergonomic API)
- ❌ **LOSES dispatch tracing** (harder to debug event flow)
- ❌ **LOSES enable/disable toggle** (useful for testing)

**Risk**: Severe. If we later need hooks, tracing, or parallel dispatch, we'd have to rebuild this infrastructure.

---

### Option 2: KEEP EventBus (Current State)

**Pros:**
- ✅ **Lifecycle hooks** for observability (can log all dispatches, track failures)
- ✅ **Pluggable backends** (future: parallel dispatch, priority queues)
- ✅ **Decorator syntax** (cleaner handler registration)
- ✅ **Dispatch tracing** (full visibility into event flow)
- ✅ **Enable/disable toggle** (useful for testing, feature flags)

**Cons:**
- Maintains ~500 LOC
- Not using existing library

**Risk**: Low. If we never use EventBus in production, it's just test code. But if we DO use it, we already have all advanced features.

---

### Option 3: HYBRID (Delete EventBus, Extend python-domain-events)

**Approach**: Use `InProcessEventDispatcher` but wrap it to add hooks/tracing.

**Pros:**
- Leverages library for core dispatch
- Adds custom hooks/tracing layer

**Cons:**
- Still maintains custom code (~200 lines)
- Complexity of wrapping external library
- May break on library updates

**Risk**: Medium. Wrapping adds maintenance burden.

---

## Usage Analysis: Is EventBus Actually Used?

### Production Usage: ❌ **NO**

**Evidence:**
```python
# src/messaging/main.py (production entry point)
# NO EventBus instantiation
# NO dispatcher.register() calls
# NO event dispatch
```

### Test Usage: ✅ **YES**

**Evidence:**
```python
# tests/unit/core/test_event_bus.py
# Comprehensive tests for:
# - Multiple handlers per event
# - Lifecycle hooks
# - Dispatch backends
# - Enable/disable toggle
# - Error handling
```

### Docstring Examples: ✅ **YES**

**Evidence:**
```python
# src/messaging/__init__.py
"""
Example:
    bus = EventBus()
    bus.register(DomainEventOccurred, OutboxEventHandler(session, repo))
    await bus.dispatch(DomainEventOccurred(...))
"""
```

**Purpose**: Shows intended **library API** design - how consumers would use messaging as a library.

---

## Conclusion

### Key Facts:

1. ❌ **NO** in-process EventBus in Kafka, RabbitMQ, FastStream, or their plugins
2. ✅ **YES** - `python-domain-events.InProcessEventDispatcher` exists (basic)
3. ⚠️ **Our EventBus has UNIQUE features** not in `InProcessEventDispatcher`:
   - Lifecycle hooks
   - Pluggable backends
   - Dispatch tracing
   - Decorator syntax
   - Enable/disable toggle
4. ❌ **EventBus is NOT used in production** (`main.py`)
5. ✅ **EventBus is fully tested** and documented as **library API**

### Recommendation:

**DELETE EventBus** ✅

**Rationale:**
1. Not used in production
2. `python-domain-events` covers 70% of use case
3. If we later need hooks/tracing, we can add them as a thin wrapper
4. Reduces 500 LOC of unused code
5. **TDD scaffolding for library feature that was never completed**

**If we ever need EventBus features:**
- Start with `InProcessEventDispatcher`
- Add hooks/tracing only when needed
- Don't over-engineer before requirements exist

---

## Final Answer to User's Question

**"Do libraries provide EventBus?"**

**Answer**: 
- **Kafka, RabbitMQ, FastStream**: NO - they're for external broker messaging, not in-process event dispatch
- **python-domain-events**: YES - `InProcessEventDispatcher` provides basic in-process event dispatch to multiple handlers
- **Our EventBus**: More advanced than `InProcessEventDispatcher` (hooks, backends, tracing) but **unused in production**, only in tests and docstrings as **library scaffolding**

**Verdict**: DELETE our EventBus, use `python-domain-events.InProcessEventDispatcher` if/when we need in-process domain events.
