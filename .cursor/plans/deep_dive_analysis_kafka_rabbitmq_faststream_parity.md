# Deep-dive analysis: Kafka plugins, RabbitMQ plugins, FastStream parity

> **STATUS: INCORPORATED** - The findings from this deep dive have been fully integrated into the main feature plan (`add_eventing_features_12bad60a.plan.md`). FastStream middleware patterns are now the standard approach across the board.

## Findings summary

After reviewing all three layers -- Kafka ecosystem, RabbitMQ ecosystem, and FastStream integration -- the following picture emerges:

### 1. Kafka plugins and extensions that overlap with EXISTING or PLANNED code

- **Exactly-once semantics (EOS)**: Since 0.11 Kafka natively provides idempotent producer (`enable.idempotence=true`), transactions (`transactional.id`), and consumer `isolation.level=read_committed` to discard aborted transactions. Our codebase sets `enable_idempotence=True` via FastStream defaults. Our own `IdempotentConsumerBase` with `SqlAlchemyProcessedMessageStore` adds a **second** deduplication layer at the application level. The native Kafka EOS covers the transport-level deduplication; our application-level deduplication covers the case where a message is replayed or a consumer instance restarts and the internal offset is behind. Conclusion: **keep only the application-level idempotency store** and drop any custom "idempotent producer" wrapper we might have planned.
  
- **Kafka Connect offset management**: Kafka Connect natively tracks and commits consumer offsets. If we ever used Kafka Connect as a replacement for our outbox publisher, the offset bookkeeping would be free. However, Connect is a separate runtime, not a Python library, and our current FastStream-based outbox publisher already handles offsets through manual `msg.ack()` or `AckPolicy.NACK_ON_ERROR`.

- **Kafka Streams**: Kafka Streams SDK (Java/Scala only) provides built-in windowing, state stores, joins, and exactly-once processing. We use FastStream Python instead, so this is not directly applicable.

**Verdict on Kafka plugins**: The only Kafka plugin that could eliminate our own code is **Kafka Connect** as a replacement for our custom outbox publisher worker. That would be a major architecture change and is out of scope. For now, we should rely on Kafka's built-in EOS for transport, and only keep application-level idempotency for edge cases (replay, crash recovery).

### 2. RabbitMQ plugins and extensions

RabbitMQ ships with many broker-side plugins (enabled via `rabbitmq-plugins enable`):

- **rabbitmq_management** - Web UI, REST API for queues, exchanges, channels, DLQ inspection. This alone could replace our planned DLQ admin API (Feature 9) if we just document the management UI endpoint. But it requires RabbitMQ server access, not application code.

- **rabbitmq_shovel** - Replicates messages between brokers. Not relevant for our use case.

- **rabbitmq_federation** - Cross-datacenter message replication. Not relevant.

- **rabbitmq_consistent_hash_exchange** - Consistent-hashing exchange for partitioned work. Kafka already provides partitioning by key natively; no overlap.

- **rabbitmq_delayed_message_exchange** - Delays message before delivery to a queue. Could replace our planned retry/circuit-breaker middleware if we configure a delayed exchange instead of application-level retry. **But** our retry middleware in FastStream (Python) is more flexible and allows custom logic (DLQ routing, schema validation) before the delay.

- **rabbitmq_prometheus** - Native Prometheus metrics endpoint at `/metrics`. If we enable this broker-side plugin, we no longer need a custom Prometheus exporter for RabbitMQ at the application level. **However**, RabbitMQ itself does not expose per-consumer or per-queue processing metrics -- only broker-level counters. Our application-level metrics (events processed, DLQ rate, latency) are still needed.

- **rabbitmq_tracing** - Broker-level message tracing. Useful for debugging but does not replace OpenTelemetry distributed tracing (which spans across multiple microservices).

**Verdict on RabbitMQ plugins**: `rabbitmq_management` and `rabbitmq_prometheus` can reduce some work, but neither eliminates our application-level code. They are infra-level concerns, not code-level replacements.

### 3. FastStream RabbitMQ integration -- parity check against Kafka

FastStream treats RabbitMQ as a **first-class broker** with full feature coverage:

| Feature | Kafka support in FastStream | RabbitMQ support in FastStream | Notes |
|---|---|---|---|
| Subscriber decorator | `@broker.subscriber("topic", group_id="g")` | `@broker.subscriber("queue", exchange=...)` | Same API surface |
| Publisher decorator | `@broker.publisher("out-topic")` | `@broker.publisher("out-queue", exchange=...)` | Full parity |
| AckPolicy | `ACK_FIRST`, `ACK`, `REJECT_ON_ERROR`, `NACK_ON_ERROR`, `MANUAL` | Same (via `msg.ack()`, `msg.nack()`) | Full parity |
| Middleware | `BaseMiddleware` with `consume_scope`, `publish_scope`, `on_receive`, `after_processed` | Same | Full parity |
| OpenTelemetry middleware | `faststream.opentelemetry.middleware.TelemetryMiddleware` | **SAME** middleware works with RabbitBroker | Full parity |
| Prometheus middleware | Broker-specific: `KafkaPrometheusMiddleware` | No Rabbit-specific Prometheus middleware listed | **GAP**: RabbitMQ Prometheus middleware not yet available in FastStream |
| Retry middleware (custom) | Full support | Full support | Full parity |
| Exchange/queue declaration | N/A (Kafka uses topics, partitions) | `declare_queue`, `declare_exchange`, `bind` | RabbitMQ-specific, more complex |
| Consumer groups | `group_id` parameter | RabbitMQ does NOT have native consumer groups -- uses multiple consumers on same queue with round-robin | **DIFFERENCE**: Not a gap, architectural difference |
| Offset tracking / replay | `seek()`, `position()` on KafkaMessage | Not applicable -- RabbitMQ does not have offset; messages are consumed and acked | **DIFFERENCE**: No replay in RabbitMQ |
| TestClient | `KafkaTestClient` | `RabbitTestClient` (via `RabbitBroker().start()` with `MockedRabbitBroker`) | Full parity |

**Critical findings:**

1. **FastStream RabbitMQ integration HAS full parity with Kafka** for the core features: subscribe, publish, ack/nack, middleware, OTel integration, test client.

2. **The only missing piece in FastStream is a RabbitMQ-specific Prometheus middleware.** FastStream ships `KafkaPrometheusMiddleware` and `NatsPrometheusMiddleware` but no `RabbitPrometheusMiddleware`. We would need to either:
   - Write a custom Prometheus middleware for RabbitMQ (using `BaseMiddleware`)
   - Rely on RabbitMQ's broker-side `rabbitmq_prometheus` plugin and scrape it separately
   - Write application-level metrics manually (which we already planned to do)

3. **RabbitMQ does NOT support offset tracking or event replay.** This means Feature 6 (event replay API) must remain Kafka-only. RabbitMQ is "consume and forget" -- once acked, the message is gone.

4. **RabbitMQ does NOT have consumer groups.** Load balancing is achieved by having multiple consumers on the same queue (round-robin by the broker). For partitioned parallelism you need multiple queues.

### 4. Features we can DROP from the plan or SIMPLIFY

After this deep analysis, here is what changes:

| Planned feature | Changed by | Action |
|---|---|---|
| Feature 2: Wire OpenTelemetry | FastStream has `TelemetryMiddleware` for BOTH Kafka and RabbitMQ | **KEEP but SIMPLIFY** to 2 lines: `broker.add_middleware(TelemetryMiddleware)` per broker |
| Feature 12: Prometheus metrics | FastStream has `KafkaPrometheusMiddleware`; no RabbitMQ one | **KEEP for Kafka** (2 lines); **MANUAL for RabbitMQ** (write custom middleware or use broker plugin) |
| Feature 9: DLQ admin API | RabbitMQ has `rabbitmq_management` REST API | **KEEP** our FastAPI DLQ query API (it queries our own outbox_events table), but we can skip any custom DLQ "resend" UI -- use management UI instead |
| Feature 3: Circuit breaker | NOT covered by any broker/plugin | **KEEP** -- still needs custom implementation |
| Feature 7: Rate limiting | NOT covered by any broker/plugin | **KEEP** -- still needs custom implementation with `aiolimiter` |
| Feature 5: Kafka consumer group config | Kafka native; FastStream wraps it | **KEEP** -- needs configuration for partition assignment strategy, static group membership |
| Feature 8: Kafka-to-RabbitMQ bridge | Neither plugin covers this bridge pattern | **KEEP** -- core architectural feature |
| Feature 1: Schema registry | NOT covered by any plugin | **KEEP** -- still needs custom implementation |
| Feature 10: Contract testing | NOT covered by any plugin | **KEEP** -- still needs custom implementation |
| Feature 6: Event replay API | Kafka native (offset seek); RabbitMQ has no equivalent | **KEEP** -- Kafka only, our outbox table queries cover it |

### 5. Existing code that could be REMOVED

Scanning the current codebase:

- **`IdempotentConsumerBase`** -- keeps application-level deduplication. **KEEP** because Kafka EOS covers transport but not replay scenarios or idempotency across broker restarts.
  
- **Custom retry wrapper / poison message handling** -- If we wire FastStream's `AckPolicy.NACK_ON_ERROR` + `RetryMiddleware`, our custom retry loop becomes redundant. **POTENTIAL REMOVAL** if the existing dead-letter handler already relies on `Msg.nack()` instead of a custom retry counter.

- **Dead letter queue infrastructure** -- If we use RabbitMQ's native `rabbitmq_management` plugin for DLQ inspection AND FastStream's `msg.nack()` for routing to DLQ queues, some of our manual `DeadLetterMessagePublisher` code might become redundant.

### 6. Final recommendation

1. **Do not add any new Kafka or RabbitMQ plugins at the broker level.** Stick to the existing Kafka broker and add RabbitMQ broker with default plugins.

2. **Use FastStream's built-in middleware everywhere possible:**
   - OpenTelemetry: `TelemetryMiddleware` (both brokers)
   - Retry: Custom `RetryMiddleware` via `BaseMiddleware` (both brokers)
   - Prometheus: Kafka native middleware, custom for RabbitMQ
   - Ack policies: Use `AckPolicy.NACK_ON_ERROR` for both brokers

3. **Keep features that no plugin covers:** Schema registry, circuit breaker, rate limiter, contract validation, DLQ admin API, event replay, Kafka-to-RabbitMQ bridge.

4. **Drop any planned custom implementations of:** retry wrapper (use FastStream middleware), OTel wiring (use FastStream middleware), Kafka consumer group offset management (use FastStream's `group_id` + `AckPolicy`).
