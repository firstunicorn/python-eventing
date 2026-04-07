# Complete library coverage analysis (Phase 1)

**Date**: 2026-04-06  
**Purpose**: Full documentation analysis for Kafka, RabbitMQ, FastStream, and python-web-toolkit to identify existing features that might replace custom code

---

## FastStream complete feature list

### Middleware system
- **BaseMiddleware** class with hooks:
  - `consume_scope(call_next, msg)` - wrap message consumption
  - `publish_scope(call_next, cmd)` - wrap message publishing
  - `on_receive()` - called on message receipt
  - `after_processed(exc_type, exc_val, exc_tb)` - called after handler completes
- **Built-in middleware patterns**:
  - `RetryMiddleware` - exponential backoff retry pattern (MAX_RETRIES=3, sleep=2**attempt)
  - `TelemetryMiddleware` - OpenTelemetry integration (traces, spans)
  - `KafkaPrometheusMiddleware` - Prometheus metrics for Kafka
  - Custom middleware for RabbitMQ Prometheus (not built-in, requires implementation)
- **Context access**: `self.context.get_local("message")`, `self.context.get_local("logger")`

### Error handling & acknowledgement
- **AckPolicy options**:
  - `REJECT_ON_ERROR` (default) - reject message on error
  - `NACK_ON_ERROR` - negative acknowledge for redelivery
  - `ACK_FIRST` - acknowledge before processing (high throughput, potential loss)
  - `ACK` - acknowledge regardless of success/failure
  - `MANUAL` - full manual control via `message.ack()`, `message.nack()`, `message.reject()`
- **Manual acknowledgement**:
  ```python
  from faststream.rabbit.annotations import RabbitMessage
  await msg.ack()  # or msg.nack() or msg.reject()
  ```
- FastStream detects manual ack and skips automatic handling

### Health checks & observability
- **`make_ping_asgi(broker, timeout=5.0)`**: Ready-to-use health check endpoint
  - Performs broker ping
  - Returns HTTP 204 on success, 500 on failure
  - Can be mounted as ASGI route: `app.mount("/health", make_ping_asgi(broker))`
- **Readiness probe pattern**:
  ```python
  async def readiness(broker, redis, postgres):
      await broker.ping(timeout=5.0)  # Check broker connectivity
      await redis.ping()  # Check Redis
      await postgres.fetchval("SELECT 1")  # Check Postgres
  ```
- **Liveness probe**: Simple 204 response
- **AsyncAPI documentation**: Auto-generated API docs from broker definitions

### Broker wrappers
- **KafkaBroker**: Wraps aiokafka/kafka-python
  - `broker.publish()` - publish messages
  - `conf` parameter - pass arbitrary `librdkafka` config as list of tuples
  - Middleware registration: `KafkaBroker(middlewares=[...])`
- **RabbitBroker**: Wraps aio-pika
  - `broker.publish()` - publish messages
  - Middleware registration: `RabbitBroker(middlewares=[...])`
- **Lifecycle hooks**: `broker.start()`, `broker.stop()`, `broker.connect()`, `broker.close()`

### Limitations discovered
- **RetryMiddleware is for consumers only**: Designed for `consume_scope`, not for `publish_scope` (producer retries)
- **No built-in DLQ routing**: AckPolicy controls ack/nack behavior, but DLQ topic naming/routing is manual
- **No built-in circuit breaker**: KIP-693 is Kafka-specific, no general-purpose circuit breaker middleware exists
- **No built-in rate limiting**: Must use external library like `aiolimiter` with custom middleware
- **Health check is basic**: `make_ping_asgi()` only checks broker ping, not custom metrics like outbox lag

---

## Kafka complete feature list

### Producer reliability
- **Retry configuration**:
  - `retries` - number of retry attempts (default: MAX_INT)
  - `retry.backoff.ms` - backoff between retries (default: 100ms)
  - `delivery.timeout.ms` - total time for delivery (default: 120s)
  - `request.timeout.ms` - timeout for single request (default: 30s)
  - `max.in.flight.requests.per.connection` - pipelining control (default: 5)
- **Idempotent producer**:
  - `enable.idempotence=true` - exactly-once producer semantics
  - Automatically retries without duplicates
- **Transactions**:
  - `transactional.id` - enable transactional delivery
  - Atomic produce + offset commit (exactly-once processing)
  - `isolation.level=read_committed` - consumers skip uncommitted transactions

### Consumer reliability
- **Consumer group configuration** (all via `conf` parameter in FastStream):
  - `group.id` - consumer group name
  - `group.instance.id` - static membership for sticky assignment
  - `partition.assignment.strategy` - `range`, `roundrobin`, `sticky`, `cooperative-sticky`
  - `max.poll.interval.ms` - max time between polls (default: 300s)
  - `session.timeout.ms` - session timeout (default: 10s)
  - `heartbeat.interval.ms` - heartbeat frequency (default: 3s)
  - `enable.auto.commit` - auto offset commit (default: true)
  - `auto.offset.reset` - `earliest`, `latest`, `none`
- **Offset management**:
  - `auto.commit.interval.ms` - commit frequency (default: 5s)
  - Manual commit: `consumer.commit()`
  - Offset tracking provides **at-least-once** semantics by default
  - Exactly-once requires transactional consumers (`isolation.level=read_committed`)

### Error handling & resilience
- **KIP-693**: Client-side circuit breaker for partition errors (Kafka 3.6+)
  - Partition-specific, not general-purpose
  - Automatically pauses failed partitions
- **Broker-side quotas**: Throttling for clients exceeding limits
- **DLQ pattern**: Convention-based (publish to `*.DLQ` topic), not built-in

### Admin API capabilities
- **Consumer groups**: Describe, delete, reset offsets
- **Topics**: Create, delete, list partitions
- **Offsets**: Query log-end-offset, current-offset, lag
- **ACLs**: Manage access control

### Kafka Connect (plugins)
- **Sink/source connectors**: Pre-built integrations (JDBC, S3, Elasticsearch, etc.)
- **Error handling**:
  - Retry policies: `errors.retry.timeout`, `errors.retry.delay.max.ms`
  - Dead letter queue: `errors.deadletterqueue.topic.name`, `errors.deadletterqueue.context.headers.enable=true`
  - Error tolerance: `errors.tolerance=all` (continue on error)
- **Not suitable for our use case**: Kafka Connect lacks flexibility for custom business logic (schema validation, routing rules, middleware integration)

---

## RabbitMQ complete feature list

### Reliability features
- **Consumer acknowledgements**:
  - **Automatic ack**: Fire-and-forget (less safe, higher throughput)
  - **Manual ack**: `basic.ack`, `basic.nack`, `basic.reject`
  - QoS: `prefetch_count` - limit unacked messages per consumer
- **Publisher confirms**:
  - Broker confirms message receipt
  - Provides at-least-once delivery guarantee
- **Dead Letter Exchange (DLX)**:
  - Route failed messages to DLX
  - Configure per queue: `x-dead-letter-exchange`, `x-dead-letter-routing-key`
  - Triggers: Message rejected/nacked, TTL expired, queue length exceeded
- **TTL (Time-To-Live)**:
  - Per-message: `expiration` property (e.g., `60000` for 60s)
  - Per-queue: `x-message-ttl` argument
  - Dead lettering on expiry (quorum/classic queues)
- **Connection recovery**: Automatic reconnection on network failure

### Flow control & backpressure
- **QoS (Quality of Service)**:
  - `prefetch_count` - limit concurrent message processing
  - Native flow control - broker pauses producers when consumers overwhelmed
- **Backpressure**: Built-in broker-side flow control

### RabbitMQ plugins
- **rabbitmq_management**:
  - HTTP API on port 15672 (Basic Auth)
  - Endpoints: `/api/overview`, `/api/queues`, `/api/exchanges`, `/api/connections`
  - CRUD operations: Create/delete queues, publish messages, get metrics
  - Higher overhead than Prometheus (development use)
- **rabbitmq_prometheus**:
  - Metrics on port 15692
  - Prometheus text format: `rabbitmq_connections_total`, `rabbitmq_queues_total`, etc.
  - Low overhead, production-ready
- **rabbitmq_shovel**:
  - Message routing between brokers
  - Dynamic shovels via HTTP API: `GET /api/shovels`
  - Requires `rabbitmq_shovel_management` plugin for HTTP API
- **rabbitmq_federation**:
  - Multi-cluster message distribution
  - Peer-to-peer topology
- **rabbitmq_stream**:
  - Stream queue type (append-only log)
  - Similar to Kafka topics (offset-based)
- **Tier 1 plugins** (core):
  - `rabbitmq_federation_management` - federation status in management UI
  - `rabbitmq_jms_topic_exchange` - JMS client integration

### Limitations discovered
- **No built-in retry middleware**: Retry must be implemented via DLX + TTL delay queues
- **No built-in circuit breaker**: Must implement custom logic
- **Management API is basic**: HTTP API provides CRUD but no rich DLQ administration (batch retry, error type filtering, audit logging)

---

## python-web-toolkit complete feature list

### python-outbox-core
- **IOutboxEvent**: Abstract base for events (Pydantic + ABC)
  - Fields: `event_id`, `event_type`, `aggregate_id`, `occurred_at`, `source`, `data_version`, `correlation_id`, `causation_id`
  - Methods: `to_message()` (serialize), `get_partition_key()` (Kafka routing)
- **OutboxPublisherBase**: Template method pattern for batch publishing
  - `publish_batch(limit)` - fetch and publish unpublished events
  - `schedule_publishing()` - abstract method (projects implement scheduling)
  - Handles: Batch fetching, publishing, marking as published
  - **CRITICAL**: Delegates retry logic to projects (no built-in retry)
- **OutboxErrorHandler**: Per-event error handling
  - `handle(event, exception)` - log error with context
  - `should_retry(event, exception, attempt)` - decide if retry (default: attempt < max_retries)
  - `is_transient_error(exception)` - detect transient errors
  - **Default max_retries=3** - but retry implementation is project responsibility
- **OutboxMetrics**: Structured logging (no Prometheus metrics)
  - `log_success(event)`, `log_batch_complete(published, total)`, `log_batch_started(batch_size)`, `log_no_events()`
  - **Does NOT provide** Prometheus counters/histograms (projects must extend)
- **OutboxHealthCheck**: Interface only (projects implement `is_healthy()`)
  - **Does NOT provide** built-in health check logic (e.g., outbox lag monitoring)
- **OutboxConfig**: Configuration dataclass (Pydantic BaseModel)
  - Fields: `batch_size`, `poll_interval_seconds`, `max_retry_count`, `retry_backoff_multiplier`, `enable_metrics`, `enable_health_check`
  - Environment variable support: `OUTBOX_*` prefix
- **IEventPublisher**: Interface for broker-agnostic publishing
  - `publish(message)` - abstract method (projects implement for Kafka/RabbitMQ/SQS)
  - **Does NOT provide** retry logic (delegated to implementations)
- **IOutboxRepository**: Interface for database operations
  - `add_event(event)`, `get_unpublished(limit, offset)`, `mark_published(event_id)`, `mark_failed(event_id)`
- **CloudEventsFormatter**: CloudEvents 1.0 formatter
  - `format(event)` - convert IOutboxEvent to CloudEvents format
  - `get_content_type()` - return `application/cloudevents+json`
- **Example adapters**:
  - `PartitionKeyRouter` - Kafka partition routing by aggregate_id
  - `KafkaRoutingFormatter` - CloudEvents + Kafka metadata
  - `KongSimpleFormatter` - CloudEvents + Kong AI Gateway metadata

### fastapi-middleware-toolkit
- **CORS**: `setup_cors_middleware(app, allowed_origins, ...)` - secure defaults
- **Error handlers**: `setup_error_handlers(app, custom_exception_class)` - global exception handlers
- **Cache control**: `CacheControlMiddleware`, `setup_cache_control_middleware(app)` - default Cache-Control headers
- **Lifespan**: `create_lifespan_manager(on_startup, on_shutdown)` - lifecycle context manager
- **Health check**: `create_health_check_endpoint(service_name, version)` - basic health check factory
  - Returns: `{"status": "healthy", "service": "...", "version": "..."}`
  - **Does NOT support** custom checks (database, outbox lag, broker)

### python-cqrs-core
- **ICommand**, **ICommandHandler**: Write operation interfaces
- **IQuery**, **IQueryHandler**: Read operation interfaces
- **BaseCommand**: Pydantic command with tracing fields
  - Fields: `trace_id`, `correlation_id`, `requested_by`, `requested_at`
- **BaseQuery**: Pydantic query with tracing fields
- **PaginatedQuery**: Query with `page`, `page_size`, `offset` property

### python-domain-events
- **BaseDomainEvent**: Base class for domain events
- **IDomainEventHandler**: Event handler interface
- **InProcessEventDispatcher**: In-process event bus
  - `register(event_type, handler)` - register handler
  - `dispatch(event)` - dispatch event to registered handlers
  - **CRITICAL**: Designed for **internal domain events** (within application), NOT external broker messaging

### gridflow-python-mediator
- **Mediator**: Request/response dispatcher
- **PipelineBehavior**: Protocol for cross-cutting concerns
- **LoggingBehavior**: Logs request handling
- **TimingBehavior**: Times request execution
- **ValidationBehavior**: Validates Pydantic models before dispatch

### python-structlog-config
- **configure_structlog**: Configure structlog with OTel/Sentry integration
  - Parameters: `log_level`, `json_output`, `enable_otel`, `enable_sentry`, `sentry_dsn`, `service_name`, `environment`
- **get_logger**: Get configured structlog logger

---

## Key findings: What's NOT provided by libraries

### 1. Retry logic for outbox publisher
- **python-outbox-core**: `OutboxPublisherBase` does NOT implement retry logic
- **python-outbox-core**: `OutboxErrorHandler` provides `should_retry()` decision logic but NO retry loop
- **Conclusion**: Our `tenacity.AsyncRetrying` in `publish_logic.py` is **necessary custom code**

### 2. Dead letter handling
- **Kafka**: DLQ is a naming convention (publish to `*.DLQ` topic), not built-in routing
- **RabbitMQ**: DLX requires manual configuration (`x-dead-letter-exchange`)
- **FastStream**: No built-in DLQ routing (AckPolicy controls ack/nack, not routing)
- **python-outbox-core**: No DLQ support (projects must implement)
- **Conclusion**: Our custom DLQ handler (6 files) provides header enrichment (retry_count, error_message) and routing logic not covered by libraries

### 3. Consumer idempotency (DB-backed)
- **Kafka**: Offset tracking provides **at-least-once** semantics only
- **Kafka**: Exactly-once requires transactional consumers (`isolation.level=read_committed`)
- **FastStream**: No built-in idempotency beyond Kafka offset tracking
- **Conclusion**: Our database "claim" mechanism (4+ files) provides **exactly-once** semantics for business logic, beyond Kafka's offset tracking

### 4. Health checks (outbox lag)
- **FastStream**: `make_ping_asgi()` checks broker ping only, not custom metrics
- **fastapi-middleware-toolkit**: `create_health_check_endpoint()` returns basic `{"status": "healthy"}`, no custom checks
- **python-outbox-core**: `OutboxHealthCheck` is an interface only (projects implement)
- **Conclusion**: Our custom `outbox_health_check.py` provides outbox lag monitoring (pending events count), not covered by libraries

### 5. In-process event bus
- **python-domain-events**: `InProcessEventDispatcher` is for **internal domain events** (within application)
- **FastStream**: Only for **external broker messaging** (Kafka/RabbitMQ)
- **Conclusion**: Our `core/contracts/bus/` (10+ files) serves domain events, distinct from external broker messaging

### 6. Circuit breaker (general-purpose)
- **Kafka**: KIP-693 is partition-specific circuit breaker, not general-purpose
- **FastStream**: No built-in circuit breaker middleware
- **RabbitMQ**: No built-in circuit breaker
- **Conclusion**: Our planned custom circuit breaker as FastStream middleware is necessary

### 7. Rate limiting (application-controlled)
- **Kafka**: Broker-side quotas (throttling)
- **RabbitMQ**: QoS manages concurrency, not rate
- **FastStream**: No built-in rate limiting middleware
- **Conclusion**: Our planned `aiolimiter` + FastStream middleware is necessary for client-side rate control

### 8. Custom metrics/observability
- **python-outbox-core**: `OutboxMetrics` provides structured logging only, NOT Prometheus metrics
- **FastStream**: `KafkaPrometheusMiddleware` exists, RabbitMQ Prometheus requires custom implementation
- **Conclusion**: Our custom Prometheus metrics (e.g., outbox lag gauge) are not covered by python-outbox-core

---

## Summary table: Library coverage vs existing code

| Feature | Kafka | RabbitMQ | FastStream | python-outbox-core | fastapi-middleware-toolkit | Decision |
|---------|-------|----------|------------|-------------------|---------------------------|----------|
| **Retry for outbox publishing** | Producer retries (config) | Publisher confirms | RetryMiddleware (consumer only) | NO (delegated to projects) | N/A | **KEEP tenacity** (outbox worker) |
| **Dead letter handling** | DLQ convention (manual) | DLX (manual config) | AckPolicy (no routing) | NO | N/A | **KEEP custom DLQ** (header enrichment) |
| **Consumer idempotency** | Offset tracking (at-least-once) | Ack/nack | AckPolicy | NO | N/A | **KEEP DB claim** (exactly-once) |
| **Health checks (outbox lag)** | N/A | N/A | make_ping_asgi (broker only) | Interface only | Basic health endpoint | **KEEP custom health** (outbox lag) |
| **In-process event bus** | N/A | N/A | External broker only | N/A | N/A | **KEEP if used** (domain events) |
| **Custom metrics** | N/A | N/A | KafkaPrometheusMiddleware | Structured logging only | N/A | **KEEP custom Prometheus** (outbox lag) |
| **Publisher wrappers** | N/A | N/A | broker.publish() | IEventPublisher interface | N/A | **KEEP minimal wrapper** (topic naming) |
| **Circuit breaker** | KIP-693 (partition-specific) | NO | NO | NO | N/A | **KEEP custom middleware** |
| **Rate limiting** | Broker quotas | QoS (concurrency) | NO | NO | N/A | **KEEP aiolimiter middleware** |

---

## Phase 1 complete

**Total documentation sources loaded**:
- FastStream: Complete middleware system, AckPolicy, health checks, broker wrappers
- Kafka: Producer/consumer API, reliability features, error handling, Kafka Connect
- RabbitMQ: AMQP protocol, DLX, QoS, plugins (management, prometheus, shovel, federation)
- python-web-toolkit: 17 packages (outbox-core, middleware-toolkit, cqrs-core, domain-events, structlog-config, etc.)

**Next step**: Phase 2 - Document existing code implementations with file-by-file analysis
