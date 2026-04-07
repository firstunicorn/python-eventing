# Removal/simplification plan (Phase 4)

**Date**: 2026-04-06  
**Purpose**: Final decisions on what to remove/simplify/keep with full justifications

---

## Executive summary

| Category | Count | LOC estimate | Action |
|----------|-------|--------------|--------|
| **KEEP (no changes)** | 5 implementations | ~950 LOC | Justified custom code |
| **SIMPLIFY** | 1 implementation | -42 LOC | Remove generic DLQ, use Kafka DLQ only |
| **DELETE** | 1 implementation | -500 LOC | EventBus unused (legacy code) |
| **TOTAL LOC REDUCTION** | | **~542 LOC** | ~36% reduction |

---

## Decision 1: KEEP - Retry logic (tenacity)

### Files: 1 file, 96 LOC
- `src/messaging/infrastructure/outbox/outbox_worker/publish_logic.py`

### Decision: **KEEP**

### Justification:
1. **Different layer**: Our retry is at outbox worker layer (application to broker), Kafka producer retries are at transport layer (broker communication)
2. **Different scope**: Covers application-layer errors (serialization, validation, business logic) + Kafka client errors, not just network errors
3. **FastStream RetryMiddleware is for consumers**: Designed for message consumption, NOT message publishing
4. **python-outbox-core delegates retry**: `OutboxErrorHandler` provides decision logic only (`should_retry()`), NO retry loop implementation
5. **Configurable backoff**: Uses `OutboxConfig.retry_backoff_multiplier` for exponential backoff
6. **Integration with DLQ**: On failure, routes to DLQ or marks as failed in database

### What libraries DON'T provide:
- ❌ FastStream: RetryMiddleware is consumer-side only
- ❌ Kafka: Producer retries cover transport errors only (network, timeout)
- ❌ python-outbox-core: NO retry loop implementation (delegated to projects)

### Breaking changes if removed:
- ✅ Outbox worker would need manual retry implementation (we ARE the implementation)
- ✅ Application-layer errors (validation, serialization) would not be retried
- ✅ Would need to use Kafka producer retries only (insufficient for our use case)

---

## Decision 2: SIMPLIFY - Dead letter handling (remove generic, keep Kafka)

### Files to REMOVE: 1 file, 42 LOC
- `src/messaging/infrastructure/pubsub/dead_letter_handler.py` (generic DLQ handler)

### Files to KEEP: 6 files, 300+ LOC
- `src/messaging/infrastructure/pubsub/kafka/kafka_dead_letter_handler/` (Kafka-specific DLQ)

### Decision: **SIMPLIFY** - Remove generic DLQ, use Kafka DLQ handler only

### Justification:
1. **Kafka-only deployment**: Currently only using Kafka, not RabbitMQ or other brokers
2. **Kafka DLQ provides more features**: Header enrichment, partition preservation, timestamp control
3. **Generic DLQ is redundant**: Kafka DLQ handler provides all generic DLQ features + Kafka-specific enhancements
4. **Simplifies architecture**: Single DLQ implementation instead of two

### What Kafka DLQ provides that generic doesn't:
- ✅ **Header enrichment**: `retry_count`, `error_message`, `original_topic`, `failure_timestamp`
- ✅ **Partition key preservation**: Maintains event ordering in DLQ
- ✅ **Timestamp control**: Preserves original event time

### Migration steps:
1. Update `publish_logic.py` to use `KafkaDeadLetterHandler` instead of `DeadLetterHandler`
2. Update `main.py` imports and instantiation
3. Delete `dead_letter_handler.py`
4. Run tests to verify DLQ routing still works

### Breaking changes:
- ✅ Code using `DeadLetterHandler` must switch to `KafkaDeadLetterHandler`
- ❌ NO external API changes (DLQ functionality identical)

---

## Decision 3: DELETE - In-process event bus (unused legacy code)

### Files to DELETE: 11+ files, 500+ LOC
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
├── event_bus.py (duplicate/deprecated)
├── dispatch_hooks.py
├── dispatcher_setup.py
tests/unit/core/
└── test_event_bus.py (tests only)
```

### Decision: **DELETE** - EventBus is unused in production code

### Justification:
1. **NOT used in main.py**: Application doesn't instantiate or use EventBus
2. **Only used in tests**: `test_event_bus.py` tests unused code
3. **OutboxEventHandler doesn't use it**: Uses `python-domain-events.IDomainEventHandler` instead
4. **Helper functions unused**: `dispatcher_setup.build_event_bus()` not called in production
5. **Legacy code**: Appears to be infrastructure for domain events, but never wired up

### Verification (grep results):
```bash
# EventBus instantiation:
src/messaging/core/contracts/dispatcher_setup.py:46    event_bus = EventBus(...)
tests/unit/core/test_event_bus.py                     # Tests only
src/messaging/__init__.py:22                          # Example only (docstring)
src/messaging/core/__init__.py:21                     # Example only (docstring)
```

**Conclusion**: EventBus is NOT used in `main.py` or any production code

### Alternative: python-domain-events
If domain events are needed, use `python-domain-events.InProcessEventDispatcher` instead:
```python
from python_domain_events import InProcessEventDispatcher

dispatcher = InProcessEventDispatcher()
dispatcher.register(UserCreated, NotifyHandler())
dispatcher.dispatch(UserCreated(user_id=1))
```

### Migration steps:
1. Confirm EventBus is not used in production (grep + code review)
2. Delete `src/messaging/core/contracts/bus/` directory (7+ files)
3. Delete `src/messaging/core/contracts/event_bus.py` (duplicate)
4. Delete `src/messaging/core/contracts/dispatch_hooks.py`
5. Delete `src/messaging/core/contracts/dispatcher_setup.py`
6. Delete `tests/unit/core/test_event_bus.py`
7. Update `src/messaging/__init__.py` and `src/messaging/core/__init__.py` (remove EventBus examples from docstrings)

### Breaking changes:
- ❌ NO breaking changes (code is unused)

---

## Decision 4: KEEP - Consumer idempotency (DB-backed claim)

### Files: 7+ files, 300+ LOC
```
src/messaging/infrastructure/pubsub/consumer_base/
├── kafka_consumer_base.py (49 LOC)
├── consumer_consume.py
├── consumer_validators.py
src/messaging/infrastructure/persistence/processed_message_store/
├── processed_message_store.py (90 LOC)
├── claim_helpers.py
├── duplicate_checker.py
src/messaging/infrastructure/persistence/orm_models/
└── processed_message_orm.py
```

### Decision: **KEEP**

### Justification:
1. **Kafka offset tracking is at-least-once**: Allows duplicate message processing
2. **Kafka exactly-once requires complex setup**: Transactional consumers + idempotent producers (overkill for our use case)
3. **DB claim provides simple exactly-once**: Prevents double-processing without Kafka transactions
4. **Critical for non-idempotent operations**: Financial transactions, inventory updates, email notifications, audit logs
5. **Atomic with business logic**: Claim + side effects in same database transaction

### What libraries DON'T provide:
- ❌ Kafka: Offset tracking is at-least-once by default (duplicates possible on replay)
- ❌ Kafka exactly-once: Requires `isolation.level=read_committed` + `transactional.id` (complex)
- ❌ RabbitMQ: Ack/nack is at-least-once only
- ❌ FastStream: No built-in idempotency beyond Kafka offset tracking

### Use cases requiring exactly-once:
1. **Financial transactions**: Prevent duplicate charges/payments
2. **Inventory updates**: Prevent double-decrement (negative stock)
3. **Email notifications**: Prevent duplicate sends (bad UX)
4. **Audit logs**: Ensure single processing entry (compliance)

### Breaking changes if removed:
- ✅ Non-idempotent operations would process twice on message replay
- ✅ Would need manual idempotency checks in every consumer
- ✅ Would need to implement Kafka transactions (complex, overkill)

---

## Decision 5: KEEP - Health checks (outbox lag monitoring)

### Files: 2 files, 150 LOC
- `src/messaging/infrastructure/health/outbox_health_check.py` (68 LOC)
- `src/messaging/infrastructure/health/checkers.py`

### Decision: **KEEP** (with minor simplification opportunity)

### Justification:
1. **Outbox lag monitoring is critical**: Detects worker failures (events piling up)
2. **FastStream make_ping_asgi() is insufficient**: Only checks broker connectivity (binary success/failure)
3. **fastapi-middleware-toolkit is basic**: Returns `{"status": "healthy"}` only, no custom checks
4. **python-outbox-core is interface only**: `OutboxHealthCheck` requires implementation (we ARE the implementation)
5. **Three-level status is valuable**: HEALTHY, DEGRADED, UNHEALTHY (more granular than binary)

### What libraries DON'T provide:
- ❌ FastStream: `make_ping_asgi()` checks broker only, NOT database or outbox lag
- ❌ fastapi-middleware-toolkit: Basic status endpoint, NO custom checks
- ❌ python-outbox-core: `OutboxHealthCheck` is interface only (projects implement)

### Our health check features:
1. **Outbox lag monitoring**: Pending events count + oldest event age
2. **Lag threshold alerts**: Configurable `lag_threshold` (default: 1000)
3. **Stale event detection**: Configurable `stale_after_seconds` (default: 300)
4. **Aggregated health**: Database + broker + outbox lag
5. **Detailed response**: Per-check status + aggregated status

### Simplification opportunity:
- **Broker check**: Use `FastStream.make_ping_asgi()` for broker connectivity instead of custom implementation
- **Keep custom**: Database check + outbox lag monitoring (not covered by libraries)

### Migration steps (if simplifying broker check):
1. Import `make_ping_asgi` from FastStream
2. Mount `/health/broker` endpoint: `app.mount("/health/broker", make_ping_asgi(broker))`
3. Update `EventingHealthCheck` to call broker ping endpoint
4. Keep custom database + outbox lag checks

---

## Decision 6: KEEP - Publisher wrapper (topic naming)

### Files: 1 file, 53 LOC
- `src/messaging/infrastructure/pubsub/kafka_publisher.py`

### Decision: **KEEP**

### Justification:
1. **Topic naming convention is custom business logic**: `event_type` → `topic_name` (1:1 mapping)
2. **Default topic fallback**: `"domain-events"` if no event type specified
3. **Partition key extraction is custom field mapping**: `aggregate_id` → `key_bytes`
4. **Dual methods for flexibility**: `publish(message)` (default topic) + `publish_to_topic(topic, message)` (explicit)
5. **Minimal wrapper (53 LOC)**: Provides business value without significant overhead

### What libraries DON'T provide:
- ❌ FastStream: `broker.publish()` requires explicit `topic` and `key` parameters
- ❌ Kafka native: No topic naming convention (must specify topic)
- ❌ python-outbox-core: `IEventPublisher` is interface only (projects implement)

### Our wrapper features:
1. **Topic naming convention**: `message["eventType"]` → `topic_name` (custom business logic)
2. **Default topic fallback**: `"domain-events"` if no event type
3. **Partition key extraction**: `message["aggregateId"]` → `key_bytes` (custom field mapping)
4. **Byte encoding**: Converts string key to bytes (FastStream requirement)

### Breaking changes if removed:
- ✅ Would need manual topic resolution in every publish call
- ✅ Would need manual partition key extraction in every publish call
- ✅ DLQ routing would need direct `broker.publish()` calls (more verbose)

---

## Decision 7: N/A - Custom metrics/observability (not implemented)

### Current status: NO Prometheus metrics implemented, only structured logging

### Decision: **N/A** - No action needed (not implemented)

### If Prometheus metrics are needed (future):
Custom Prometheus middleware would be required for outbox-specific metrics:
1. **Outbox lag gauge**: `outbox_unpublished_events_total` - pending events count
2. **Publish success counter**: `outbox_publish_success_total` - successful publishes
3. **Publish failure counter**: `outbox_publish_failure_total` - failed publishes
4. **DLQ routed counter**: `outbox_dlq_routed_total` - DLQ routes
5. **Consumer claim success counter**: `consumer_claim_success_total` - successful claims
6. **Consumer claim duplicate counter**: `consumer_claim_duplicate_total` - duplicate skips

**Note**: FastStream `KafkaPrometheusMiddleware` provides Kafka consumer/producer metrics, NOT outbox-specific metrics

---

## Summary: Final decisions

| Implementation | Files | LOC | Decision | LOC change | Reason |
|---------------|-------|-----|----------|-----------|--------|
| **Retry (tenacity)** | 1 | 96 | KEEP | 0 | Different layer, python-outbox-core delegates retry |
| **DLQ (generic)** | 1 | 42 | REMOVE | -42 | Kafka DLQ handler provides all features + more |
| **DLQ (Kafka)** | 6 | 300+ | KEEP | 0 | Kafka-specific metadata enrichment |
| **Consumer idempotency** | 7+ | 300+ | KEEP | 0 | Exactly-once semantics, critical for non-idempotent operations |
| **Health checks** | 2 | 150 | KEEP | 0 | Outbox lag monitoring, FastStream/toolkit insufficient |
| **Event bus** | 11+ | 500+ | REMOVE | -500 | Unused in production (legacy code) |
| **Publisher wrapper** | 1 | 53 | KEEP | 0 | Custom topic naming + partition key extraction |
| **Prometheus metrics** | 0 | 0 | N/A | 0 | Not implemented |

**TOTAL LOC REDUCTION**: ~542 lines (36% reduction)

---

## Files to delete

### 1. Generic DLQ handler (1 file, 42 LOC):
```
src/messaging/infrastructure/pubsub/dead_letter_handler.py
```

### 2. Event bus infrastructure (11+ files, 500+ LOC):
```
src/messaging/core/contracts/bus/
├── event_bus.py
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

---

## Files to modify

### 1. Update DLQ handler usage:
```python
# src/messaging/infrastructure/outbox/outbox_worker/publish_logic.py
- from messaging.infrastructure.pubsub.dead_letter_handler import DeadLetterHandler
+ from messaging.infrastructure.pubsub.kafka.kafka_dead_letter_handler import KafkaDeadLetterHandler

# src/messaging/main.py
- DeadLetterHandler(repository, publisher)
+ KafkaDeadLetterHandler(repository, publisher)
```

### 2. Update imports (remove EventBus examples):
```python
# src/messaging/__init__.py
# Remove EventBus example from docstring

# src/messaging/core/__init__.py
# Remove EventBus example from docstring
```

---

## Dependencies to remove (pyproject.toml)

**None** - No external dependencies are being removed:
- ✅ `tenacity` - still used (KEEP)
- ✅ `sqlalchemy` - still used (KEEP)
- ✅ `faststream` - still used (KEEP)
- ✅ `python-outbox-core` - still used (KEEP)

---

## Test updates required

### 1. Delete test file:
```
tests/unit/core/test_event_bus.py
```

### 2. Update DLQ tests (if any):
- Replace `DeadLetterHandler` imports with `KafkaDeadLetterHandler`
- No functional changes (DLQ behavior identical)

---

## Estimated effort

| Task | Effort | Risk |
|------|--------|------|
| Delete generic DLQ handler | 30 min | Low (simple replacement) |
| Delete EventBus infrastructure | 1 hour | Very low (unused code) |
| Update DLQ imports | 15 min | Very low (simple import change) |
| Update docstrings | 15 min | Very low (documentation only) |
| Run tests | 30 min | Low (verify DLQ still works) |
| **TOTAL** | **2.5 hours** | **Low overall** |

---

## Phase 4 complete

**Next step**: Phase 5 - Create migration guide with before/after code examples
