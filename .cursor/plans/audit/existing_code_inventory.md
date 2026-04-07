# Existing code inventory (Phase 2)

**Date**: 2026-04-06  
**Purpose**: Complete file-by-file analysis of existing custom implementations to identify potential redundancy with libraries

---

## 1. Retry logic (tenacity-based)

### File: `src/messaging/infrastructure/outbox/outbox_worker/publish_logic.py`

**Purpose**: Retry failed event publishing with exponential backoff before routing to DLQ

**Implementation details**:
- Uses `tenacity.AsyncRetrying` with:
  - `stop=stop_after_attempt(config.max_retry_count)` (from `OutboxConfig`)
  - `wait=wait_exponential(multiplier=config.retry_backoff_multiplier)` (from `OutboxConfig`)
  - `reraise=True` - raises exception after all retries exhausted
- Retry loop wraps `await publisher.publish(event.to_message())`
- Logs retry attempts: `logger.warning("Retry %d/%d for event %s", ...)`
- On success: `await repository.mark_published(event.event_id)` + `metrics.log_success(event)`
- On failure: `error_handler.handle(event, exc)` + route to DLQ or mark failed

**Dependencies**:
- `tenacity` (AsyncRetrying, stop_after_attempt, wait_exponential)
- `python_outbox_core.OutboxConfig` (max_retry_count, retry_backoff_multiplier)
- `python_outbox_core.IEventPublisher` (publish method)
- `python_outbox_core.IOutboxRepository` (mark_published, mark_failed)
- `DeadLetterHandler` (handle method)
- `OutboxMetrics` (log_success)
- `OutboxErrorHandler` (handle method)

**LOC**: 96 lines (1 file)

**Layer**: Outbox worker publishing logic (producer-side retry)

**Key insight**: This is **producer-side** retry for outbox worker publishing to broker, NOT **consumer-side** retry for message consumption (which FastStream RetryMiddleware covers)

---

## 2. Dead letter handling (dual implementation)

### 2a. Generic DLQ handler

**File**: `src/messaging/infrastructure/pubsub/dead_letter_handler.py`

**Purpose**: Broker-agnostic DLQ handler for failed outbox events

**Implementation details**:
- Marks event as failed in database: `await self._repository.mark_failed(event.event_id, error_message)`
- Publishes to DLQ topic: `dlq_topic = f"{event.event_type}.DLQ"`
- Message format: `{"event": event.to_message(), "error": error_message}`
- Uses `KafkaEventPublisher.publish_to_topic(dlq_topic, message)`
- Logs warning + info on routing

**Dependencies**:
- `python_outbox_core.IOutboxRepository`
- `KafkaEventPublisher`
- `BaseEvent`

**LOC**: 42 lines (1 file)

---

### 2b. Kafka-specific DLQ handler

**Files** (6 files total):
1. `src/messaging/infrastructure/pubsub/kafka/kafka_dead_letter_handler/handler.py` (66 lines)
2. `src/messaging/infrastructure/pubsub/kafka/kafka_dead_letter_handler/handler_mixin.py` (mixin logic)
3. `src/messaging/infrastructure/pubsub/kafka/kafka_dead_letter_handler/config.py` (KafkaDLQConfig)
4. `src/messaging/infrastructure/pubsub/kafka/kafka_dead_letter_handler/helpers.py` (header/partition helpers)
5. `src/messaging/infrastructure/pubsub/kafka/kafka_dead_letter_handler/execution.py` (handle execution)
6. `src/messaging/infrastructure/pubsub/kafka/kafka_dead_letter_handler/logging.py` (logging utilities)

**Purpose**: Kafka-specific DLQ handler with advanced features

**Implementation details**:
- **Header enrichment**: Adds Kafka headers with error metadata, retry count, original topic
- **Partition key preservation**: Uses same partition key as original event (maintains ordering)
- **Timestamp control**: Preserves original event time
- **Configuration**: `KafkaDLQConfig(include_headers, preserve_partition_key)`
- Extends generic `DeadLetterHandler` with Kafka-specific capabilities

**Dependencies**:
- `python_outbox_core.IOutboxRepository`
- `KafkaEventPublisher`
- `KafkaDLQConfig`
- Kafka-specific headers API

**Total LOC**: ~300+ lines (6 files)

**Key insight**: Provides **Kafka-specific metadata enrichment** (headers, partition keys, timestamps) not available in generic DLQ or library implementations

---

## 3. Consumer idempotency (DB-backed claim)

### Files (4+ files):
1. `src/messaging/infrastructure/pubsub/consumer_base/kafka_consumer_base.py` (49 lines) - Base class
2. `src/messaging/infrastructure/persistence/processed_message_store/processed_message_store.py` (90 lines) - Store implementation
3. `src/messaging/infrastructure/persistence/processed_message_store/claim_helpers.py` - SQL statement builder
4. `src/messaging/infrastructure/persistence/processed_message_store/duplicate_checker.py` - Duplicate detection
5. `src/messaging/infrastructure/persistence/orm_models/processed_message_orm.py` - ORM model
6. `src/messaging/infrastructure/pubsub/consumer_base/consumer_consume.py` - Consume method
7. `src/messaging/infrastructure/pubsub/consumer_base/consumer_validators.py` - Validation

**Purpose**: Exactly-once consumer semantics via database claim mechanism

**Implementation details**:
- **IProcessedMessageStore protocol**: `claim(consumer_name, event_id) -> bool`
- **SqlAlchemyProcessedMessageStore**: Uses `INSERT ... ON CONFLICT DO NOTHING` (PostgreSQL)
- **Claim logic**:
  1. Extract `event_id` from message
  2. Attempt to insert record: `(consumer_name, event_id, processed_at)`
  3. If insert succeeds (rowcount > 0) → process event
  4. If insert fails (IntegrityError, duplicate) → skip event (idempotent)
- **Transaction management**: Starts transaction if not active, caller commits/rolls back
- **IdempotentConsumerBase**: Abstract base class with `consume(message)` method
  - Calls `consume_event(message, consumer_name, processed_message_store, handle_event_coro)`
  - Delegates to subclass `handle_event(message)` if claim succeeds

**Dependencies**:
- `sqlalchemy.ext.asyncio.AsyncSession`
- `sqlalchemy.exc.IntegrityError`
- ORM model: `ProcessedMessageORM`

**Total LOC**: ~300+ lines (7+ files)

**Layer**: Consumer-side idempotency (prevents replay double-processing)

**Key insight**: Provides **exactly-once** semantics beyond Kafka's **at-least-once** offset tracking. Prevents double-processing of replayed messages within same consumer group.

---

## 4. Health checks (outbox lag monitoring)

### Files (2 files):
1. `src/messaging/infrastructure/health/outbox_health_check.py` (68 lines) - Aggregator
2. `src/messaging/infrastructure/health/checkers.py` - Individual check implementations

**Purpose**: Aggregate health signals from database, broker, and outbox lag

**Implementation details**:
- **EventingHealthCheck** class (extends `python_outbox_core.health_check.OutboxHealthCheck`)
- **Three health checks**:
  1. **Database**: `check_database(repository)` - queries database connectivity
  2. **Broker**: `check_broker(broker)` - pings Kafka broker via `broker.ping(timeout=5.0)`
  3. **Outbox lag**: `check_outbox_lag(repository, lag_threshold, stale_after_seconds)` - queries pending events count
- **Aggregation logic**:
  - If all checks HEALTHY → HEALTHY
  - If any check DEGRADED → DEGRADED
  - If any check UNHEALTHY → UNHEALTHY
- **Response format**:
  ```python
  {
      "status": "healthy"|"degraded"|"unhealthy",
      "timestamp": "ISO 8601",
      "checks": {
          "database": {"status": "...", ...},
          "broker": {"status": "...", ...},
          "outbox": {"status": "...", "lag": 123, ...}
      }
  }
  ```

**Dependencies**:
- `FastStream.kafka.KafkaBroker`
- `python_outbox_core.health_check.OutboxHealthCheck` (interface)
- `SqlAlchemyOutboxRepository`

**Total LOC**: ~150 lines (2 files)

**Key insight**: Provides **outbox lag monitoring** (pending events count) not covered by `FastStream.make_ping_asgi()` (broker ping only) or `fastapi-middleware-toolkit.create_health_check_endpoint()` (basic status only)

---

## 5. In-process event bus (domain events)

### Files (10+ files):
1. `src/messaging/core/contracts/bus/event_bus.py` (85 lines) - Main facade
2. `src/messaging/core/contracts/bus/backends.py` - Dispatch backends (sequential, parallel)
3. `src/messaging/core/contracts/bus/dispatch_executor.py` - Handler invocation
4. `src/messaging/core/contracts/bus/handler_resolver.py` - Handler name/callback extraction
5. `src/messaging/core/contracts/bus/hook_emitter.py` - Lifecycle hook emission
6. `src/messaging/core/contracts/bus/types.py` - Type definitions
7. `src/messaging/core/contracts/bus/__init__.py` - Exports
8. `src/messaging/core/contracts/dispatch_hooks.py` - Hook definitions (DispatchHooks, DispatchTrace)
9. `src/messaging/core/contracts/dispatcher_setup.py` - Setup utilities
10. `src/messaging/core/contracts/event_bus.py` (duplicate/deprecated?)
11. `src/messaging/core/contracts/base_event.py` - BaseEvent definition

**Purpose**: In-process event dispatch for domain events within the application

**Implementation details**:
- **EventBus** class:
  - `register(event_type, handler, handler_name)` - register handler
  - `subscriber(event_type, handler_name)` - decorator for handlers
  - `dispatch(event)` - dispatch event to registered handlers
- **Dispatch backends**:
  - `SequentialDispatchBackend` - invoke handlers one by one
  - (Optional parallel backend for concurrent handlers)
- **Handler types**:
  - Async callbacks: `async def handler(event: BaseEvent) -> None`
  - Handler instances with `handle(event)` method
- **Lifecycle hooks**:
  - `on_dispatch` - before dispatching
  - `on_success` - after successful handler
  - `on_failure` - after failed handler
  - `on_disabled` - when bus is disabled
- **DispatchTrace**: Structured logging for dispatch events
- **Settings**: `DispatchSettings(enabled=True)` - enable/disable bus

**Dependencies**:
- `BaseEvent` (core event abstraction)
- `DispatchHooks` (hook definitions)
- `DispatchSettings` (configuration)

**Total LOC**: ~500+ lines (11+ files)

**Layer**: Application-level domain events (NOT external broker messaging)

**Key insight**: Designed for **internal domain events** (within application process), distinct from **external broker messaging** (FastStream for Kafka/RabbitMQ). Similar to `python-domain-events.InProcessEventDispatcher` but with more features (hooks, backends, decorators).

---

## 6. Publisher wrapper (topic naming)

### File: `src/messaging/infrastructure/pubsub/kafka_publisher.py`

**Purpose**: Kafka event publisher with topic resolution and partition key extraction

**Implementation details**:
- **KafkaEventPublisher** (implements `python_outbox_core.IEventPublisher`)
- **Topic resolution**: `_resolve_topic(message)` - extracts `eventType` or `event_type` field, defaults to `"domain-events"`
- **Partition key extraction**: Extracts `aggregateId` or `aggregate_id`, encodes to bytes
- **Methods**:
  - `publish(message)` - publish to default topic (resolved from message)
  - `publish_to_topic(topic, message)` - publish to explicit topic (used by DLQ)
- **Wraps FastStream**: `await self._broker.publish(message, topic=topic, key=key_bytes)`

**Dependencies**:
- `FastStream.kafka.KafkaBroker`
- `python_outbox_core.IEventPublisher` (interface)

**LOC**: 53 lines (1 file)

**Layer**: Infrastructure wrapper (topic naming convention)

**Key insight**: Minimal wrapper providing **topic naming convention** (event type → topic name) and **partition key encoding** (aggregate ID → bytes). This is **custom business logic** not replaceable by direct FastStream usage.

---

## 7. Custom metrics/observability

### Current usage:
- **python_outbox_core.OutboxMetrics** imported in `publish_logic.py`:
  - `metrics.log_success(event)` - structured logging only
  - **Does NOT provide** Prometheus counters/histograms
- **Structured logging** via `logger.info()`, `logger.warning()`, `logger.error()`
- **DispatchTrace** in `dispatch_hooks.py` - structured logging for in-process events

### Potential custom Prometheus metrics (NOT yet implemented in codebase):
- `outbox_lag_gauge` - pending events count
- `outbox_publish_success_counter` - successful publishes
- `outbox_publish_failure_counter` - failed publishes
- `outbox_dlq_routed_counter` - DLQ routes
- `consumer_claim_success_counter` - successful claims
- `consumer_claim_duplicate_counter` - duplicate skips

**Current status**: Only structured logging, NO Prometheus metrics implemented yet

**Key insight**: `python-outbox-core.OutboxMetrics` provides **structured logging only**, NOT Prometheus metrics. If Prometheus metrics are needed, custom implementation is required.

---

## 8. Configuration management

### File: `src/messaging/config.py`

**Purpose**: Application-specific settings extending toolkit base classes

**Implementation details**:
- **Settings class** (extends `BaseFastAPISettings` + `BaseDatabaseSettings`):
  - FastAPI settings: `app_name`, `debug`, `allowed_origins`
  - Database settings: `database_url`, `pool_size`, `pool_recycle`
  - Kafka settings: `kafka_bootstrap_servers`, `kafka_consumer_conf` (dict)
  - RabbitMQ settings: `rabbitmq_url`
  - Outbox settings: `outbox_batch_size`, `outbox_poll_interval_seconds`, `outbox_max_retry_count`, `outbox_retry_backoff_multiplier`
  - Health check settings: `health_lag_threshold`, `health_stale_after_seconds`

**Dependencies**:
- `fastapi_config_patterns.BaseFastAPISettings`
- `fastapi_config_patterns.BaseDatabaseSettings`
- `pydantic.Field`

**Key insight**: Settings extend toolkit base classes with application-specific fields. This is **expected usage** of toolkit, not redundancy.

---

## Summary: Existing implementations analysis

| Implementation | Files | LOC | Purpose | Layer |
|---------------|-------|-----|---------|-------|
| **Retry logic (tenacity)** | 1 | 96 | Producer-side retry for outbox publishing with exponential backoff | Outbox worker |
| **Dead letter handling (generic)** | 1 | 42 | Broker-agnostic DLQ routing for failed outbox events | Outbox worker |
| **Dead letter handling (Kafka)** | 6 | 300+ | Kafka-specific DLQ with header enrichment, partition preservation | Outbox worker |
| **Consumer idempotency (DB)** | 7+ | 300+ | Exactly-once consumer semantics via database claim mechanism | Consumer-side |
| **Health checks (outbox lag)** | 2 | 150 | Aggregate health signals (database, broker, outbox lag) | Infrastructure |
| **In-process event bus** | 11+ | 500+ | Domain event dispatch within application process | Application-level |
| **Publisher wrapper** | 1 | 53 | Topic naming convention and partition key encoding | Infrastructure |
| **Custom metrics** | N/A | 0 | Structured logging only (no Prometheus yet) | Observability |

**Total**: 29+ files, ~1500+ LOC of custom code

---

## Dependency graph: What imports what

### Outbox worker publishing flow:
```
outbox_worker.worker
└── outbox_worker.publish_logic (tenacity retry)
    ├── python_outbox_core.IEventPublisher (interface)
    │   └── kafka_publisher.KafkaEventPublisher (topic naming)
    │       └── faststream.kafka.KafkaBroker (FastStream)
    ├── python_outbox_core.IOutboxRepository
    │   └── outbox_repository.SqlAlchemyOutboxRepository
    ├── pubsub.dead_letter_handler.DeadLetterHandler (generic DLQ)
    │   └── kafka_publisher.KafkaEventPublisher
    └── pubsub.kafka.kafka_dead_letter_handler.KafkaDeadLetterHandler (Kafka DLQ)
        └── kafka_publisher.KafkaEventPublisher
```

### Consumer idempotency flow:
```
pubsub.consumer_base.kafka_consumer_base.IdempotentConsumerBase
└── pubsub.consumer_base.consumer_consume.consume_event
    └── pubsub.processed_message_store.IProcessedMessageStore (interface)
        └── persistence.processed_message_store.SqlAlchemyProcessedMessageStore
            └── persistence.orm_models.processed_message_orm.ProcessedMessageORM
```

### Health check flow:
```
health.outbox_health_check.EventingHealthCheck
├── health.checkers.check_database
├── health.checkers.check_broker (faststream.kafka.KafkaBroker.ping)
└── health.checkers.check_outbox_lag
    └── outbox_repository.SqlAlchemyOutboxRepository
```

### In-process event bus flow:
```
contracts.bus.event_bus.EventBus
├── contracts.bus.backends.DispatchBackend (sequential/parallel)
├── contracts.bus.dispatch_executor.DispatchExecutor
├── contracts.bus.handler_resolver.HandlerResolver
├── contracts.bus.hook_emitter.HookEmitter
│   └── contracts.dispatch_hooks.DispatchHooks
└── contracts.base_event.BaseEvent
```

---

## Phase 2 complete

**Next step**: Phase 3 - Cross-reference each existing implementation against all library documentation
