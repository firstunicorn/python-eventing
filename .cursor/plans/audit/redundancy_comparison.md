# Cross-reference comparison (Phase 3)

**Date**: 2026-04-06  
**Purpose**: Systematic comparison of each existing implementation against ALL library documentation

---

## Comparison 1: Retry logic (tenacity for outbox publishing)

| Feature | Our implementation | Kafka native | RabbitMQ native | FastStream | python-outbox-core |
|---------|-------------------|--------------|----------------|-----------|-------------------|
| **Retry mechanism** | `tenacity.AsyncRetrying` in `publish_logic.py` | Producer config: `retries`, `retry.backoff.ms` | Publisher confirms (no auto-retry) | `RetryMiddleware` (consumer only) | NO (delegated to projects) |
| **Exponential backoff** | ✅ `wait_exponential(multiplier=config.retry_backoff_multiplier)` | ✅ `retry.backoff.ms` (fixed backoff) | ❌ | ✅ `await asyncio.sleep(2**attempt)` | ❌ |
| **Max retries** | ✅ `stop_after_attempt(config.max_retry_count)` | ✅ `retries` config (default: MAX_INT) | ❌ | ✅ `MAX_RETRIES=3` (hardcoded) | ✅ `OutboxErrorHandler.max_retries=3` (decision only, no loop) |
| **Layer** | Outbox worker (publish to broker) | Kafka producer (send to broker) | N/A | Consumer (consume from broker) | Outbox worker (publish to broker) |
| **Retry loop implementation** | ✅ Full retry loop with logging | ✅ Built into librdkafka | ❌ | ✅ Full retry loop | ❌ NO retry loop (projects implement) |
| **Error handling** | ✅ `error_handler.handle(event, exc)` + DLQ routing | ✅ Producer callback | ❌ | ✅ Exception propagation | ✅ `OutboxErrorHandler.handle()` (logging only) |

### Analysis:
- **Kafka producer retries**: Cover network/timeout errors at transport layer (broker communication)
- **Our tenacity retries**: Cover application-layer errors (serialization, validation, business logic) + Kafka client errors
- **FastStream RetryMiddleware**: For **consumer-side** retry (message consumption), not **producer-side** (publishing)
- **python-outbox-core**: Provides `OutboxErrorHandler.should_retry()` decision logic but NO retry loop implementation

### Conclusion: **KEEP tenacity retry**
- **Reason 1**: Different layer - our retry is at outbox worker layer (app to broker), Kafka retry is at producer layer (broker communication)
- **Reason 2**: FastStream RetryMiddleware is for consumers, not producers
- **Reason 3**: python-outbox-core delegates retry implementation to projects (we ARE the project)
- **Reason 4**: Covers application-layer errors not handled by Kafka producer retries

---

## Comparison 2: Dead letter handling (DLQ)

| Feature | Our implementation | Kafka native | RabbitMQ native | FastStream | python-outbox-core |
|---------|-------------------|--------------|----------------|-----------|-------------------|
| **DLQ routing** | ✅ Custom topic: `f"{event.event_type}.DLQ"` | Convention (manual publish to `*.DLQ`) | ✅ Dead Letter Exchange (DLX) | ❌ (AckPolicy controls ack/nack) | ❌ |
| **Error metadata** | ✅ `{"event": ..., "error": error_message}` | ❌ (must add manually) | ✅ DLX headers (`x-death`) | ❌ | ❌ |
| **Kafka headers (retry count, original topic)** | ✅ Kafka DLQ handler (6 files) | ❌ | N/A | ❌ | ❌ |
| **Partition key preservation** | ✅ Kafka DLQ handler | ❌ (must add manually) | N/A | ❌ | ❌ |
| **Timestamp preservation** | ✅ Kafka DLQ handler | ❌ (must add manually) | N/A | ❌ | ❌ |
| **Mark as failed in DB** | ✅ `repository.mark_failed(event_id, error)` | ❌ | ❌ | ❌ | ❌ |
| **Generic vs Kafka-specific** | ✅ Both: generic (1 file) + Kafka (6 files) | Kafka-specific | RabbitMQ-specific | Broker-agnostic | ❌ |

### Analysis:
- **Kafka DLQ**: Convention-based (publish to `*.DLQ` topic), no built-in routing or metadata enrichment
- **RabbitMQ DLX**: Built-in but requires manual configuration (`x-dead-letter-exchange`)
- **FastStream AckPolicy**: Controls ack/nack behavior, but doesn't route to DLQ or add metadata
- **Kafka Connect**: Has DLQ support (`errors.deadletterqueue.topic.name`, `errors.deadletterqueue.context.headers.enable=true`) but not applicable (we're not using Kafka Connect)

### Our Kafka DLQ handler features NOT in libraries:
1. **Header enrichment**: `retry_count`, `error_message`, `original_topic`, `failure_timestamp`
2. **Partition key preservation**: Maintains event ordering in DLQ
3. **Timestamp control**: Preserves original event time
4. **Database tracking**: `mark_failed()` for audit trail
5. **Custom topic naming**: `{event_type}.DLQ` convention

### Conclusion: **KEEP custom DLQ handler**
- **Reason 1**: Kafka has NO built-in DLQ routing (convention only)
- **Reason 2**: RabbitMQ DLX not applicable (we're using Kafka for outbox)
- **Reason 3**: FastStream AckPolicy doesn't provide DLQ routing or metadata
- **Reason 4**: Kafka DLQ handler (6 files) provides Kafka-specific metadata enrichment not available elsewhere
- **Simplification opportunity**: Generic DLQ handler (1 file) could potentially be removed if we only use Kafka DLQ handler

---

## Comparison 3: Consumer idempotency (DB-backed claim)

| Feature | Our implementation | Kafka native | RabbitMQ native | FastStream | python-outbox-core |
|---------|-------------------|--------------|----------------|-----------|-------------------|
| **Idempotency mechanism** | ✅ Database claim: `INSERT ... ON CONFLICT DO NOTHING` | Offset tracking (at-least-once) | Ack/nack (at-least-once) | Kafka offset tracking | ❌ |
| **Exactly-once semantics** | ✅ Yes (database constraint) | ⚠️ Requires transactional consumers (`isolation.level=read_committed`) | ❌ | ⚠️ Requires Kafka transactions | ❌ |
| **Replay protection** | ✅ Yes (database prevents double-processing) | ❌ (offsets can be reset) | ❌ (messages can be re-delivered) | ❌ | ❌ |
| **Per-consumer tracking** | ✅ `(consumer_name, event_id)` unique constraint | Per consumer group (not per consumer) | Per consumer | Per consumer group | ❌ |
| **Transaction integration** | ✅ Atomic with business logic (caller commits) | ⚠️ Requires `enable.idempotence=true` + `transactional.id` | ❌ | ⚠️ Requires Kafka transactions | ❌ |
| **Duplicate detection** | ✅ IntegrityError → duplicate | ❌ (offset > last committed) | ❌ (nack → requeue) | ❌ | ❌ |

### Analysis:
- **Kafka offset tracking**: Provides **at-least-once** by default (message delivered at least once, possibly multiple times)
- **Kafka exactly-once**: Requires:
  1. Producer: `enable.idempotence=true` + `transactional.id`
  2. Consumer: `isolation.level=read_committed` + transactional reads
  3. Complex setup, not suitable for simple use cases
- **Our DB claim**: Simple **exactly-once** for business logic without Kafka transactions
- **RabbitMQ ack/nack**: Provides at-least-once only

### Use cases for DB claim:
1. **Financial transactions**: Prevent duplicate charges/payments
2. **Inventory updates**: Prevent double-decrement
3. **Email notifications**: Prevent duplicate sends
4. **Audit logs**: Ensure single processing entry

### Conclusion: **KEEP DB claim mechanism**
- **Reason 1**: Kafka offset tracking is **at-least-once** by default (allows duplicates)
- **Reason 2**: Kafka exactly-once requires complex transactional setup (overkill for our use case)
- **Reason 3**: Our DB claim provides simple **exactly-once** for business logic
- **Reason 4**: Prevents double-processing of replayed messages (critical for non-idempotent operations)
- **Reason 5**: Atomic with business logic (claim + side effects in same transaction)

---

## Comparison 4: Health checks (outbox lag monitoring)

| Feature | Our implementation | Kafka native | RabbitMQ native | FastStream | python-outbox-core | fastapi-middleware-toolkit |
|---------|-------------------|--------------|----------------|-----------|-------------------|---------------------------|
| **Broker ping** | ✅ `check_broker(broker)` | N/A | N/A | ✅ `make_ping_asgi(broker)` | ❌ | ❌ |
| **Database check** | ✅ `check_database(repository)` | N/A | N/A | ❌ | ❌ | ❌ |
| **Outbox lag monitoring** | ✅ `check_outbox_lag(repository, lag_threshold)` | N/A | N/A | ❌ | ✅ `OutboxHealthCheck` interface (projects implement) | ❌ |
| **Aggregated health** | ✅ `EventingHealthCheck.check_health()` | N/A | N/A | ❌ | ❌ | ✅ `create_health_check_endpoint()` (basic) |
| **Health status levels** | ✅ HEALTHY, DEGRADED, UNHEALTHY | N/A | N/A | Binary (200/500) | ✅ `HealthStatus` enum | Binary (200/500) |
| **Pending events count** | ✅ Query outbox table for unpublished count | N/A | N/A | ❌ | ❌ | ❌ |
| **Stale event detection** | ✅ Check oldest unpublished event age | N/A | N/A | ❌ | ❌ | ❌ |

### Analysis:
- **FastStream `make_ping_asgi()`**: Only checks broker connectivity (binary success/failure), not custom metrics
- **fastapi-middleware-toolkit `create_health_check_endpoint()`**: Returns basic `{"status": "healthy", "service": "...", "version": "..."}`, no custom checks
- **python-outbox-core `OutboxHealthCheck`**: Interface only (projects must implement `is_healthy()` and `check_health()`)
- **Our implementation**: Aggregates three health signals (database, broker, outbox lag) with three status levels

### Our health check features NOT in libraries:
1. **Outbox lag monitoring**: Pending events count + oldest event age
2. **Lag threshold alerts**: Configurable `lag_threshold` (default: 1000)
3. **Stale event detection**: Configurable `stale_after_seconds` (default: 300)
4. **Three-level status**: HEALTHY, DEGRADED, UNHEALTHY (not binary)
5. **Detailed response**: Per-check status + aggregated status

### Conclusion: **KEEP custom health checks**
- **Reason 1**: FastStream `make_ping_asgi()` only checks broker, not database or outbox lag
- **Reason 2**: fastapi-middleware-toolkit provides basic status only, no custom checks
- **Reason 3**: python-outbox-core `OutboxHealthCheck` is interface only (we ARE the implementation)
- **Reason 4**: Outbox lag monitoring is critical for detecting worker failures (not covered by libraries)
- **Simplification opportunity**: Use FastStream `make_ping_asgi()` for broker check, keep custom database + outbox lag checks

---

## Comparison 5: In-process event bus (domain events)

| Feature | Our implementation | python-domain-events | gridflow-python-mediator | FastStream |
|---------|-------------------|---------------------|-------------------------|-----------|
| **Purpose** | In-process domain events | In-process domain events | Request/response (CQRS) | External broker messaging |
| **Event dispatch** | ✅ `EventBus.dispatch(event)` | ✅ `InProcessEventDispatcher.dispatch(event)` | ✅ `Mediator.send(request)` | ❌ (external broker) |
| **Handler registration** | ✅ `EventBus.register(event_type, handler)` | ✅ `dispatcher.register(event_type, handler)` | ✅ `mediator.register_handler(request, handler)` | ❌ |
| **Multiple handlers per event** | ✅ Yes (list of handlers) | ❓ (need to verify) | ❌ (one handler per request) | N/A |
| **Decorator registration** | ✅ `@bus.subscriber(event_type)` | ❌ | ❌ | ✅ `@broker.subscriber(...)` |
| **Lifecycle hooks** | ✅ `on_dispatch`, `on_success`, `on_failure`, `on_disabled` | ❌ | ✅ `PipelineBehavior` (pre/post processing) | ❌ |
| **Dispatch backends** | ✅ Sequential, (optional parallel) | ❓ | Sequential only | N/A |
| **DispatchTrace** | ✅ Structured logging | ❌ | ✅ `LoggingBehavior`, `TimingBehavior` | N/A |
| **Enable/disable** | ✅ `DispatchSettings(enabled=True)` | ❌ | ❌ | N/A |

### Analysis:
- **python-domain-events `InProcessEventDispatcher`**: Designed for internal domain events (within application)
- **gridflow-python-mediator `Mediator`**: Designed for CQRS pattern (commands/queries), NOT domain events
- **FastStream**: Designed for **external broker messaging** (Kafka/RabbitMQ), NOT in-process events
- **Our EventBus**: Designed for in-process domain events with lifecycle hooks, backends, and decorators

### Key differences from python-domain-events:
1. **Lifecycle hooks**: `on_dispatch`, `on_success`, `on_failure` (not in python-domain-events)
2. **Dispatch backends**: Sequential/parallel (need to verify python-domain-events support)
3. **Decorator registration**: `@bus.subscriber(event_type)` (not in python-domain-events)
4. **Enable/disable**: `DispatchSettings(enabled=True)` (not in python-domain-events)
5. **DispatchTrace**: Structured logging for dispatch events (not in python-domain-events)

### Questions to answer:
1. Does `python-domain-events.InProcessEventDispatcher` support multiple handlers per event?
2. Does `python-domain-events` support parallel dispatch?
3. Does `python-domain-events` support lifecycle hooks or behaviors?
4. **Is our EventBus actively used in the codebase?** (need to grep for usage)

### Conclusion: **VERIFY USAGE, THEN DECIDE**
- **If EventBus is actively used**: Compare features with `python-domain-events.InProcessEventDispatcher`
  - If python-domain-events covers all our needs → **MIGRATE to python-domain-events**
  - If we need extra features (hooks, backends) → **KEEP EventBus**
- **If EventBus is NOT used**: **DELETE entire `core/contracts/bus/` directory (10+ files, 500+ LOC)**

---

## Comparison 6: Publisher wrapper (topic naming)

| Feature | Our implementation | Kafka native | FastStream | python-outbox-core |
|---------|-------------------|--------------|-----------|-------------------|
| **Topic resolution** | ✅ `_resolve_topic(message)` extracts `eventType`/`event_type` | ❌ (must specify topic) | ❌ (must specify topic) | ❌ (IEventPublisher interface only) |
| **Default topic** | ✅ `"domain-events"` if no event type | ❌ | ❌ | ❌ |
| **Partition key extraction** | ✅ Extracts `aggregateId`/`aggregate_id`, encodes to bytes | ❌ (must provide key) | ✅ `broker.publish(..., key=...)` | ❌ (IEventPublisher interface only) |
| **Topic naming convention** | ✅ `event_type` → `topic_name` (1:1 mapping) | ❌ | ❌ | ❌ |
| **Explicit topic publishing** | ✅ `publish_to_topic(topic, message)` for DLQ | ✅ `producer.send(topic, ...)` | ✅ `broker.publish(..., topic=...)` | ❌ |

### Analysis:
- **FastStream `broker.publish()`**: Requires explicit `topic` and `key` parameters
- **python-outbox-core `IEventPublisher`**: Interface only (projects implement)
- **Our wrapper**: Provides topic naming convention (event type → topic name) + partition key extraction

### Our wrapper features:
1. **Topic naming convention**: `message["eventType"]` → `topic_name` (custom business logic)
2. **Default topic fallback**: `"domain-events"` if no event type
3. **Partition key extraction**: `message["aggregateId"]` → `key_bytes` (custom field mapping)
4. **Dual methods**: `publish(message)` (default topic) + `publish_to_topic(topic, message)` (explicit)

### Conclusion: **KEEP wrapper (minimal)**
- **Reason 1**: Topic naming convention is **custom business logic** (event type → topic name)
- **Reason 2**: Partition key extraction is **custom field mapping** (aggregate ID → bytes)
- **Reason 3**: Wrapper is minimal (53 LOC) and provides business value
- **Reason 4**: python-outbox-core `IEventPublisher` is interface only (we ARE the implementation)

---

## Comparison 7: Custom metrics/observability

| Feature | Our implementation | FastStream | python-outbox-core | RabbitMQ plugins |
|---------|-------------------|-----------|-------------------|-----------------|
| **Structured logging** | ✅ `logger.info()`, `logger.warning()` | ✅ Built-in logging | ✅ `OutboxMetrics.log_success()` | ❌ |
| **Prometheus metrics** | ❌ (not implemented) | ✅ `KafkaPrometheusMiddleware` | ❌ (structured logging only) | ✅ `rabbitmq_prometheus` |
| **Custom counters** | ❌ | ❌ (must add custom) | ❌ | ❌ |
| **Custom gauges (outbox lag)** | ❌ (not implemented) | ❌ | ❌ | ❌ |
| **Histogram (publish duration)** | ❌ | ❌ | ❌ | ❌ |

### Analysis:
- **Current status**: Only structured logging, NO Prometheus metrics implemented
- **FastStream `KafkaPrometheusMiddleware`**: Provides Kafka consumer/producer metrics, NOT outbox-specific metrics
- **python-outbox-core `OutboxMetrics`**: Provides structured logging only, NOT Prometheus metrics
- **RabbitMQ prometheus plugin**: Provides RabbitMQ-specific metrics, NOT outbox-specific metrics

### If Prometheus metrics are needed (future):
1. **Outbox lag gauge**: `outbox_unpublished_events_total` - pending events count
2. **Publish success counter**: `outbox_publish_success_total` - successful publishes
3. **Publish failure counter**: `outbox_publish_failure_total` - failed publishes
4. **DLQ routed counter**: `outbox_dlq_routed_total` - DLQ routes
5. **Consumer claim success counter**: `consumer_claim_success_total` - successful claims
6. **Consumer claim duplicate counter**: `consumer_claim_duplicate_total` - duplicate skips

### Conclusion: **NO ACTION NEEDED (not implemented)**
- **Current status**: Only structured logging, NO custom Prometheus metrics
- **If metrics are needed**: Implement custom Prometheus middleware (NOT redundant, libraries don't cover outbox-specific metrics)

---

## Summary table: Redundancy analysis

| Implementation | Kafka | RabbitMQ | FastStream | python-outbox-core | fastapi-middleware-toolkit | python-domain-events | Decision |
|---------------|-------|----------|------------|-------------------|---------------------------|---------------------|----------|
| **Retry (tenacity)** | Producer retries (transport) | NO | Consumer retries | NO (delegated) | N/A | N/A | **KEEP** (different layer) |
| **DLQ (generic)** | Convention | DLX | NO | NO | N/A | N/A | **SIMPLIFY** (use Kafka DLQ only) |
| **DLQ (Kafka)** | Convention | N/A | NO | NO | N/A | N/A | **KEEP** (metadata enrichment) |
| **Consumer idempotency** | At-least-once | At-least-once | At-least-once | NO | N/A | N/A | **KEEP** (exactly-once) |
| **Health (outbox lag)** | N/A | N/A | Broker ping only | Interface only | Basic only | N/A | **KEEP** (custom metrics) |
| **Event bus** | N/A | N/A | External only | N/A | N/A | YES | **VERIFY USAGE** → KEEP or DELETE |
| **Publisher wrapper** | NO | N/A | NO | Interface only | N/A | N/A | **KEEP** (custom logic) |
| **Prometheus metrics** | N/A | N/A | Kafka metrics | NO | N/A | N/A | **N/A** (not implemented) |

---

## Phase 3 complete

**Key findings**:
1. **KEEP (5 implementations)**: Retry, Kafka DLQ, Consumer idempotency, Health checks, Publisher wrapper
2. **SIMPLIFY (1 implementation)**: Generic DLQ → use Kafka DLQ only
3. **VERIFY USAGE (1 implementation)**: Event bus → grep for usage, then KEEP or DELETE
4. **N/A (1 implementation)**: Prometheus metrics → not implemented yet

**Next step**: Phase 4 - Generate removal/simplification decisions with justifications
