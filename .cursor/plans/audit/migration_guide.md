# Migration guide (Phase 5)

**Date**: 2026-04-06  
**Purpose**: Step-by-step migration instructions with before/after code examples

---

## Overview

This migration removes redundant code while preserving all functionality:
- **LOC reduction**: ~542 lines (36% reduction)
- **Breaking changes**: Minimal (only internal imports)
- **Estimated effort**: 2.5 hours
- **Risk level**: Low

---

## Migration 1: Simplify DLQ handler (remove generic, use Kafka only)

### Step 1.1: Update `publish_logic.py` import

**File**: `src/messaging/infrastructure/outbox/outbox_worker/publish_logic.py`

**Before**:
```python
from messaging.infrastructure.pubsub.dead_letter_handler import DeadLetterHandler
```

**After**:
```python
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler import KafkaDeadLetterHandler
```

**Type signature change**:
```python
async def try_publish(
    event: BaseEvent,
    *,
    publisher: IEventPublisher,
    repository: IOutboxRepository,
    config: OutboxConfig,
    dead_letter_handler: DeadLetterHandler | None,  # BEFORE
    dead_letter_handler: KafkaDeadLetterHandler | None,  # AFTER
    metrics: OutboxMetrics,
    error_handler: OutboxErrorHandler,
) -> bool:
```

**No functional changes needed** - method signature is identical

---

### Step 1.2: Update `main.py` instantiation

**File**: `src/messaging/main.py`

**Before**:
```python
from messaging.infrastructure import (
    DeadLetterHandler,
    EventingHealthCheck,
    KafkaEventPublisher,
    ScheduledOutboxWorker,
    SqlAlchemyOutboxRepository,
    build_outbox_config,
    create_kafka_broker,
    create_session_factory,
)

# ...

worker = ScheduledOutboxWorker(
    repository=repository,
    publisher=publisher,
    config=build_outbox_config(settings),
    dead_letter_handler=DeadLetterHandler(repository, publisher),
)
```

**After**:
```python
from messaging.infrastructure import (
    EventingHealthCheck,
    KafkaDeadLetterHandler,  # Changed from DeadLetterHandler
    KafkaEventPublisher,
    ScheduledOutboxWorker,
    SqlAlchemyOutboxRepository,
    build_outbox_config,
    create_kafka_broker,
    create_session_factory,
)

# ...

worker = ScheduledOutboxWorker(
    repository=repository,
    publisher=publisher,
    config=build_outbox_config(settings),
    dead_letter_handler=KafkaDeadLetterHandler(  # Changed from DeadLetterHandler
        repository,
        publisher,
        include_headers=True,  # Optional: Kafka-specific feature (default: True)
        preserve_partition_key=True,  # Optional: Kafka-specific feature (default: True)
    ),
)
```

**New Kafka-specific features** (optional):
- `include_headers=True` - Add error metadata headers (retry count, error message, original topic)
- `preserve_partition_key=True` - Maintain event ordering in DLQ

---

### Step 1.3: Update `__init__.py` exports

**File**: `src/messaging/infrastructure/pubsub/__init__.py`

**Before**:
```python
from .dead_letter_handler import DeadLetterHandler
from .kafka_publisher import KafkaEventPublisher
# ...

__all__ = [
    "DeadLetterHandler",
    "KafkaEventPublisher",
    # ...
]
```

**After**:
```python
from .kafka.kafka_dead_letter_handler import KafkaDeadLetterHandler
from .kafka_publisher import KafkaEventPublisher
# ...

__all__ = [
    "KafkaDeadLetterHandler",  # Changed from DeadLetterHandler
    "KafkaEventPublisher",
    # ...
]
```

---

### Step 1.4: Delete generic DLQ handler

**Command**:
```bash
rm src/messaging/infrastructure/pubsub/dead_letter_handler.py
```

**Verification**:
```bash
# Check for any remaining imports of DeadLetterHandler
rg "from.*dead_letter_handler import DeadLetterHandler" --type py
rg "import.*DeadLetterHandler" --type py
```

**Expected result**: No matches (all imports updated)

---

## Migration 2: Delete unused EventBus infrastructure

### Step 2.1: Verify EventBus is unused

**Command**:
```bash
# Check for EventBus instantiation in production code
rg "EventBus\(\)" --type py --glob "!tests/**" --glob "!src/messaging/core/contracts/bus/**"
```

**Expected result**: Only docstring examples in `__init__.py` files (safe to remove)

---

### Step 2.2: Update docstrings (remove EventBus examples)

**File**: `src/messaging/__init__.py`

**Before**:
```python
"""
Eventing microservice.

Example:
>>> event_bus = build_event_bus()
>>> # ... EventBus usage ...
"""
```

**After**:
```python
"""
Eventing microservice.

Provides transactional outbox pattern for reliable event publishing.
"""
```

---

**File**: `src/messaging/core/__init__.py`

**Before**:
```python
"""
Core event contracts and bus infrastructure.

Example:
>>> bus = EventBus()
>>> # ... EventBus usage ...
"""
```

**After**:
```python
"""
Core event contracts for domain events.

Provides base event classes and event registry for type management.
"""
```

---

### Step 2.3: Delete EventBus infrastructure

**Commands**:
```bash
# Delete EventBus implementation files
rm -rf src/messaging/core/contracts/bus/

# Delete related contract files
rm src/messaging/core/contracts/event_bus.py  # Duplicate/deprecated
rm src/messaging/core/contracts/dispatch_hooks.py
rm src/messaging/core/contracts/dispatcher_setup.py

# Delete EventBus tests
rm tests/unit/core/test_event_bus.py
```

**File list (11+ files deleted)**:
```
src/messaging/core/contracts/bus/
├── event_bus.py (85 LOC)
├── backends.py
├── dispatch_executor.py
├── handler_resolver.py
├── hook_emitter.py
├── types.py
├── __init__.py
src/messaging/core/contracts/
├── event_bus.py (duplicate)
├── dispatch_hooks.py
├── dispatcher_setup.py
tests/unit/core/
└── test_event_bus.py
```

**LOC reduction**: ~500 lines

---

### Step 2.4: Update imports (remove EventBus exports)

**File**: `src/messaging/core/contracts/__init__.py`

**Before**:
```python
from .base_event import BaseEvent
from .event_bus import EventBus
from .event_envelope import EventEnvelope
from .event_registry import EventRegistry
# ...

__all__ = [
    "BaseEvent",
    "EventBus",
    "EventEnvelope",
    "EventRegistry",
    # ...
]
```

**After**:
```python
from .base_event import BaseEvent
from .event_envelope import EventEnvelope
from .event_registry import EventRegistry
# ...

__all__ = [
    "BaseEvent",
    # "EventBus",  # REMOVED (unused legacy code)
    "EventEnvelope",
    "EventRegistry",
    # ...
]
```

---

### Step 2.5: Verify no broken imports

**Commands**:
```bash
# Check for any remaining imports of EventBus
rg "from messaging.core.contracts import.*EventBus" --type py
rg "from messaging.core.contracts.bus" --type py
rg "from messaging.core.contracts.dispatch_hooks" --type py
```

**Expected result**: No matches (all deleted)

---

## Testing strategy

### Step 3.1: Unit tests (DLQ migration)

**Test file**: `tests/unit/infrastructure/test_dead_letter_handler.py` (if exists)

**Update imports**:
```python
# Before
from messaging.infrastructure.pubsub.dead_letter_handler import DeadLetterHandler

# After
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler import KafkaDeadLetterHandler
```

**Update instantiation**:
```python
# Before
handler = DeadLetterHandler(repository, publisher)

# After
handler = KafkaDeadLetterHandler(repository, publisher)
```

**No functional test changes needed** - DLQ behavior is identical

---

### Step 3.2: Integration tests (outbox worker)

**Test files**: `tests/integration/test_outbox_*`

**Expected behavior** (no changes):
1. ✅ Events are published to broker after retry attempts
2. ✅ Failed events are routed to DLQ topic (`{event_type}.DLQ`)
3. ✅ DLQ messages contain error information
4. **NEW**: ✅ Kafka DLQ messages include headers (retry count, error message, original topic)
5. **NEW**: ✅ Kafka DLQ messages preserve partition key

**Test command**:
```bash
cd c:\coding\gridflow-microservices-codex-taskmaster\microservices\eventing && python -m uv run --extra test pytest tests/integration/test_outbox_* -v
```

---

### Step 3.3: Verify EventBus deletion (no broken tests)

**Test command**:
```bash
cd c:\coding\gridflow-microservices-codex-taskmaster\microservices\eventing && python -m uv run --extra test pytest tests/ -v -k "not test_event_bus"
```

**Expected result**: All tests pass (EventBus tests skipped)

**If any test fails**:
1. Check for EventBus imports in test file
2. Remove EventBus usage or delete test if testing EventBus only

---

## Configuration changes

**No configuration changes needed** - all changes are internal implementation details

---

## Deployment considerations

### Pre-deployment checklist:
- [ ] All tests pass (unit + integration)
- [ ] DLQ routing verified in integration tests
- [ ] No EventBus imports remain in codebase
- [ ] Kafka DLQ handler features documented (headers, partition key preservation)

### Deployment steps:
1. **Deploy code changes**: Standard deployment (no special steps)
2. **Monitor DLQ topics**: Verify DLQ messages still arrive at `{event_type}.DLQ` topics
3. **Check DLQ message format**: Verify Kafka headers are present (`retry_count`, `error_message`, `original_topic`)
4. **Check partition keys**: Verify DLQ messages maintain same partition key as original events

### Rollback plan:
If issues occur:
1. **Revert commit**: `git revert <commit-sha>`
2. **Redeploy previous version**: Standard deployment
3. **No data loss**: DLQ messages use same topic naming convention (`{event_type}.DLQ`)

---

## Breaking changes summary

| Change | Affected code | Impact | Migration effort |
|--------|--------------|--------|-----------------|
| **DeadLetterHandler → KafkaDeadLetterHandler** | `main.py`, `publish_logic.py`, `__init__.py` | Import change only | 15 min |
| **EventBus deletion** | Tests only | Delete unused tests | 30 min |

**No external API changes** - all changes are internal implementation details

---

## Verification checklist

After migration, verify:

### 1. DLQ functionality:
- [ ] Failed events route to DLQ topics
- [ ] DLQ topic naming: `{event_type}.DLQ`
- [ ] DLQ messages contain error information
- [ ] **NEW**: DLQ messages include Kafka headers
- [ ] **NEW**: DLQ messages preserve partition key

### 2. Imports and exports:
- [ ] No `DeadLetterHandler` imports remain
- [ ] No `EventBus` imports remain
- [ ] No broken imports (run tests)

### 3. File structure:
- [ ] `dead_letter_handler.py` deleted
- [ ] `bus/` directory deleted
- [ ] EventBus-related files deleted (11+ files)

### 4. Tests:
- [ ] All tests pass (except EventBus tests)
- [ ] Integration tests verify DLQ routing
- [ ] No test failures from migration

---

## Code snippets: Before/after comparison

### Example 1: Outbox worker setup

**Before** (generic DLQ):
```python
from messaging.infrastructure.pubsub.dead_letter_handler import DeadLetterHandler

worker = ScheduledOutboxWorker(
    repository=repository,
    publisher=publisher,
    config=build_outbox_config(settings),
    dead_letter_handler=DeadLetterHandler(repository, publisher),
)
```

**After** (Kafka DLQ with features):
```python
from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler import KafkaDeadLetterHandler

worker = ScheduledOutboxWorker(
    repository=repository,
    publisher=publisher,
    config=build_outbox_config(settings),
    dead_letter_handler=KafkaDeadLetterHandler(
        repository,
        publisher,
        include_headers=True,  # Add error metadata headers
        preserve_partition_key=True,  # Maintain event ordering
    ),
)
```

**Benefits**:
- ✅ Kafka-specific metadata enrichment (headers)
- ✅ Partition key preservation (event ordering in DLQ)
- ✅ Timestamp control (preserves original event time)

---

### Example 2: DLQ message format

**Before** (generic DLQ):
```json
{
  "event": {
    "event_id": "uuid",
    "event_type": "user.created",
    "aggregate_id": "user-123",
    ...
  },
  "error": "Failed to publish: ConnectionError"
}
```

**After** (Kafka DLQ with headers):
```json
{
  "event": {
    "event_id": "uuid",
    "event_type": "user.created",
    "aggregate_id": "user-123",
    ...
  },
  "error": "Failed to publish: ConnectionError"
}

Headers:
{
  "retry_count": "3",
  "error_message": "Failed to publish: ConnectionError",
  "original_topic": "user.created",
  "failure_timestamp": "2026-04-06T12:34:56.789Z"
}

Partition key: "user-123" (preserved from original event)
```

**Benefits**:
- ✅ Rich error metadata in Kafka headers
- ✅ Partition key preserved (maintains ordering)
- ✅ Original topic tracked (for replay purposes)

---

## Alternative: If python-domain-events is needed

If domain events are needed in the future, use `python-domain-events` instead of custom EventBus:

### Installation:
```bash
pip install python-domain-events
```

### Usage:
```python
from python_domain_events import BaseDomainEvent, IDomainEventHandler, InProcessEventDispatcher

# Define event
class UserCreated(BaseDomainEvent):
    event_type: str = "user_created"
    user_id: int

# Define handler
class NotifyHandler(IDomainEventHandler[UserCreated]):
    async def handle(self, event: UserCreated) -> None:
        print(f"User {event.user_id} created")

# Setup dispatcher
dispatcher = InProcessEventDispatcher()
dispatcher.register(UserCreated, NotifyHandler())

# Dispatch event
await dispatcher.dispatch(UserCreated(user_id=1))
```

**Benefits over custom EventBus**:
- ✅ Well-maintained library (part of python-web-toolkit)
- ✅ Simpler API (no backends, hooks, settings)
- ✅ Standard domain events pattern

---

## Post-migration cleanup

### Optional: Enable mypy strict mode
Since EventBus infrastructure is removed, consider enabling stricter type checking:

**pyproject.toml**:
```toml
[tool.mypy]
strict = true
warn_unused_ignores = true
```

### Optional: Update documentation
Update project README or architecture docs to reflect:
1. ✅ Kafka DLQ handler with metadata enrichment
2. ✅ EventBus removed (legacy code)
3. ✅ Simplified architecture diagram

---

## Estimated timeline

| Task | Time | Cumulative |
|------|------|-----------|
| **Update DLQ imports** (3 files) | 15 min | 15 min |
| **Delete EventBus files** (11+ files) | 30 min | 45 min |
| **Update docstrings** (2 files) | 15 min | 60 min |
| **Run tests** (verify no breakage) | 30 min | 90 min |
| **Integration test** (verify DLQ) | 30 min | 120 min |
| **Code review** | 30 min | 150 min |
| **TOTAL** | | **2.5 hours** |

---

## Success criteria

Migration is complete when:
- [ ] All files deleted (12+ files, ~542 LOC)
- [ ] All imports updated (3 files)
- [ ] All tests pass (except EventBus tests)
- [ ] DLQ routing verified (integration test)
- [ ] Kafka DLQ headers verified (message inspection)
- [ ] Code review approved
- [ ] Deployed to staging environment
- [ ] Monitoring shows DLQ messages arriving correctly

---

## Phase 5 complete

**All phases completed successfully**:
1. ✅ Phase 1: Library documentation loaded
2. ✅ Phase 2: Existing code inventory created
3. ✅ Phase 3: Cross-reference comparison completed
4. ✅ Phase 4: Removal plan generated
5. ✅ Phase 5: Migration guide created

**Summary**:
- **LOC reduction**: ~542 lines (36% reduction)
- **Files deleted**: 12+ files
- **Breaking changes**: Minimal (internal imports only)
- **Estimated effort**: 2.5 hours
- **Risk level**: Low

**Ready for implementation**: All analysis and planning complete
