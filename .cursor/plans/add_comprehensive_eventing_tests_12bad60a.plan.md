---
name: Add comprehensive eventing tests
overview: "Add 10 new test groups covering eventing system best practices: event ordering, poison messages, event contract validation, consumer groups, outbox recovery, e2e flow, health degradation, chaos resilience, serialization edge cases, and concurrency."
todos:
  - id: apply-audit-updates
    content: "Review tests logic to reflect audit decisions (e.g. generic DLQ removal)"
    status: done
  - id: unit-infrastructure-untested
    content: "Add unit tests: consumer_validators, consumer_helpers, dead_letter_handler, outbox_queries, outbox_config"
    status: done
  - id: integration-e2e-flow
    content: "Add integration test: e2e event flow (full publish→outbox→kafka→consume pipeline)"
    status: done
  - id: property-event-contracts
    content: "Add property-based test: event contract/schema validation"
    status: done
  - id: property-serialization-edges
    content: "Add property-based test: serialization edge cases (unicode, large payloads, date edges)"
    status: done
  - id: integration-kafka-ordering
    content: "Add integration test: Kafka event ordering and partition keys"
    status: done
  - id: integration-poison-message
    content: "Add integration test: Kafka poison message handling"
    status: done
  - id: integration-consumer-groups
    content: "Add integration test: consumer groups and offset management"
    status: done
  - id: integration-outbox-recovery
    content: "Add integration test: outbox worker failure recovery"
    status: done
  - id: chaos-kafka-resilience
    content: "Add chaos test: Kafka connection resilience (broker up/down)"
    status: done
  - id: integration-concurrent-processing
    content: "Add integration test: concurrent processing and claim races"
    status: done
  - id: unit-health-degradation
    content: "Add unit test: health degradation status transitions"
    status: done
  - id: run-all-checks
    content: Run all linters and tests to verify everything passes
    status: done
isProject: false
---

## New test groups (10 groups, organized by folder)

All test files must stay under 75-100 lines each. Use existing fixtures from `tests/conftest.py` and `tests/unit/infrastructure/conftest.py`. Use Hypothesis property-based patterns where applicable. Use Testcontainers for integration tests.

**Serena MCP requirement**: When referencing or reusing existing test fixtures, fake classes, or source code symbols (e.g., `FakeRepository`, `RecordingPublisher`, `IdempotentConsumerBase`, `SqlAlchemyProcessedMessageStore`, `OutboxMetrics`), use Serena MCP to verify symbol signatures and extract code structures. Do not guess at class/method signatures. If Serena MCP is not working, ask the user to enable it before proceeding with implementation.

### Test folder structure

```
tests/
├── integration/
│   ├── test_e2e_event_flow.py              (e2e: full publish→outbox→kafka→consume pipeline)
│   ├── test_kafka_ordering.py              (partition key ordering guarantees)
│   ├── test_kafka_consumer_groups.py       (consumer group rebalancing, offset commits)
│   ├── test_kafka_poison_message.py        (malformed messages routed to DLQ, no block)
│   └── test_outbox_recovery.py             (crash recovery, metrics accuracy, batch limits)
├── unit/infrastructure/
│   ├── test_consumer_validators.py         (message validation functions)
│   ├── test_consumer_helpers.py            (helper functions)
│   ├── test_dead_letter_handler.py         (DLQ handler isolation)
│   ├── test_outbox_queries.py              (query construction)
│   └── test_outbox_config.py               (config building)
├── property_based/core/
│   ├── test_event_contract_validation.py   (schema validation, arbitrary payloads)
│   └── test_serialization_edge_cases.py    (unicode, large payloads, date edges)
├── chaos/
│   ├── __init__.py
│   └── test_kafka_connection_resilience.py (broker up/down, reconnection)
├── unit/infrastructure/
│   └── test_health_degradation.py          (health status transitions, degradation curve)
└── integration/
    └── test_concurrent_processing.py       (concurrent consumers, claim races)
```

---

### Group 1: Unit tests for untested infrastructure modules

**Files: `tests/unit/infrastructure/test_consumer_validators.py`**

Test `src/messaging/infrastructure/pubsub/consumer_base/consumer_validators.py`:
- `validate_event_id_or_raise(message: dict)` -- asserts raises `ValueError` for missing `eventId`/`event_id`
- Asserts passes when `eventId` present
- Test with empty string, None, non-string types

**Files: `tests/unit/infrastructure/test_consumer_helpers.py`**

Test `src/messaging/infrastructure/pubsub/consumer_base/consumer_helpers.py`:
- Extract event_id from various message formats (camelCase, snake_case, nested)
- Handle missing keys gracefully

**Files: `tests/unit/infrastructure/test_dead_letter_handler.py`**

Test `src/messaging/infrastructure/pubsub/kafka/kafka_dead_letter_handler/handler.py`:
- `KafkaDeadLetterHandler.handle_failure(event, error)` routes to `{eventType}.DLQ` topic
- Test with valid event, malformed event, missing eventType
- Verify header enrichment (retry_count, error_message, original_topic, failure_timestamp)
- Verify partition key preservation

**Files: `tests/unit/infrastructure/test_outbox_queries.py`**

Test `src/messaging/infrastructure/outbox/outbox_queries.py`:
- `select_unpublished(limit, offset)` generates correct SQLAlchemy query with WHERE `published=False`
- `update_published(event_id)` generates correct update statement
- `update_failed(event_id, error)` generates correct update with error_message
- Test query structure and bound parameters

**Files: `tests/unit/infrastructure/test_outbox_config.py`**

Test `src/messaging/infrastructure/outbox/outbox_config.py`:
- `build_outbox_config(settings)` maps all fields correctly
- Test with min/max values for batch_size (1, 1000), poll_interval (0.1, 60.0)

---

### Group 2: E2E event flow

**Files: `tests/integration/test_e2e_event_flow.py`**

Full pipeline test using Testcontainers (Postgres + Kafka):
1. Create `SqlAlchemyOutboxRepository` with real SQLite/Postgres session
2. Create `KafkaEventPublisher` with real Kafka broker
3. Create `EventRegistry` with registered `ExampleEvent`
4. Use `EventBus` to publish event via outbox pattern
5. Assert event persisted to outbox (unpublished)
6. Run `ScheduledOutboxWorker.publish_batch()` to move event from outbox to Kafka
7. Consume from Kafka with `AIOKafkaConsumer(auto_offset_reset="earliest")`
8. Assert received message matches original event data

Key fixtures: reuse `docker_or_skip`, create inline Postgres + Kafka containers. Use `RecordingConsumer(IdempotentConsumerBase)` from `processed_message_consumers.py` to validate consumer-side processing.

---

### Group 3: Event contract/schema validation (property-based)

**Files: `tests/property_based/core/test_event_contract_validation.py`**

Use Hypothesis strategies to generate arbitrary payloads:
- `@given(invalid_payloads)` -- generate dicts missing required fields, wrong types
- Assert `EventRegistry.deserialize()` raises `UnknownEventTypeError` or `pydantic.ValidationError` for invalid payloads
- Assert valid payloads with extra unknown fields are accepted (forward compatibility)
- Test `BaseEvent.from_dict()` with missing `eventType`, missing `aggregateId`, missing `timestamp`
- Generate payloads with `eventType` values of wrong types (int, list, None)

---

### Group 4: Serialization edge cases (property-based)

**Files: `tests/property_based/core/test_serialization_edge_cases.py`**

Use Hypothesis text strategies for edge cases:
- UTF-8 edge cases: emojis, CJK characters, bidi text, combining characters
- Large payloads: text approaching Kafka message size limits (1MB)
- DateTime timezone edges: UTC, DST transitions, maximum/minimum valid timestamps
- Null/None fields in optional event payload fields
- Empty strings vs None
- Assert serialization/deserialization is lossless: `event.to_message()` → `registry.deserialize()` → `== event`

Reuse `_SAFE_TEXT` strategy from existing `test_event_properties.py`, extend with `_UNICODE_TEXT`, `_LARGE_TEXT`, `_EDGE_DATETIMES`.

---

### Group 5: Kafka event ordering and partition keys

**Files: `tests/integration/test_kafka_ordering.py`**

Using Testcontainers with real Kafka:
- Publish N events (e.g., 50) with same partition key `order-123`
- Publish N events with different partition key `order-456`
- Consume all messages, assert ordering per partition key is preserved
- Assert events interleaved across different partition keys (no cross-partition ordering guarantee)
- Use `AIOKafkaConsumer` with `auto_offset_reset="earliest"`, `enable_auto_commit=False`

---

### Group 6: Kafka poison message handling

**Files: `tests/integration/test_kafka_poison_message.py`**

Using Testcontainers with real Kafka:
- Publish a deliberately corrupted JSON payload (e.g., `b"not-json{{{")` to a Kafka topic
- Start consumer for that topic (`RecordingConsumer` or `FailingConsumer`)
- Assert consumer does not crash: continues processing next valid message
- Publish a valid event after the poison message
- Assert valid event is consumed successfully
- Assert DLQ topic receives the poison message (use `KafkaEventPublisher` or direct DLQ handler to verify)

Reuses `ProcessedMessageConsumers` from `tests/integration/processed_message_consumers.py`.

---

### Group 7: Consumer groups and offset management

**Files: `tests/integration/test_kafka_consumer_groups.py`**

Using Testcontainers with real Kafka:
- **Test group ID sharing**: Launch 2 consumers with same `group_id`, publish 20 events, assert events distributed across consumers (no duplicates)
- **Test different group IDs**: Launch 2 consumers with different `group_ids`, publish 10 events, assert each consumer receives all 10
- **Test offset commit and resume**: Consume 5 events, commit offsets, kill consumer, restart consumer, publish 5 more, assert resumed from offset 5 (only gets new 5)

Uses `AIOKafkaConsumer` with explicit `group_id` parameter and `enable_auto_commit=False`.

---

### Group 8: Outbox worker failure recovery

**Files: `tests/integration/test_outbox_recovery.py`**

Using real SQLite/Postgres session (reuse `sqlite_session_factory` fixture):
- **Test crash mid-batch**: Persist 20 outbox events, create `ScheduledOutboxWorker` with `RecordingPublisher(should_fail=True)` for first 10 calls, `should_fail=False` for remaining. Run `publish_batch()`, assert 10 failed, 0 published. Fix publisher (`should_fail=False`), run again, assert 10 published.
- **Test metrics accuracy**: Assert `OutboxMetrics` `success_count`, `failure_count`, `total_processed` match actual counts after mixed success/failure run.
- **Test batch size enforcement**: Persist 50 events, worker with `batch_size=5`, assert `publish_batch()` returns at most 5, remaining 45 still unpublished.

Reuses `RecordingPublisher` from `test_outbox_worker_flow.py`.

---

### Group 9: Kafka connection resilience (chaos tests)

**Files: `tests/chaos/__init__.py`** (empty)

**Files: `tests/chaos/test_kafka_connection_resilience.py`**

Using Testcontainers:
- **Test publish during Kafka shutdown**: Publish event, kill Kafka container mid-batch, assert `KafkaEventPublisher` raises appropriate exception (not hangs forever)
- **Test consumer reconnect**: Start consumer, kill Kafka container, restart Kafka container, assert consumer reconnects and resumes consuming
- **Test publisher recovery**: Kill and restart Kafka container, assert publisher works after restart
- Mark with `@pytest.mark.chaos` and `@pytest.mark.timeout(600)` (10 min timeout)

Uses `docker_or_skip` fixture and container `stop()`/`start()` methods.

---

### Group 10: Concurrent processing and claim races

**Files: `tests/integration/test_concurrent_processing.py`**

- **Test concurrent claim race**: Use `asyncio.gather()` to launch 2 `RecordingConsumer` instances processing same event stream with same `consumer_name`. Assert only one succeeds in claiming, the other gets blocked (`claim` returns False).
- **Test concurrent different consumer names**: Same event stream, different `consumer_name`, assert both succeed independently.
- **Test concurrent outbox access**: Two concurrent `publish_batch()` calls from simulated workers, assert no double-publish (idempotency via `ON CONFLICT DO NOTHING`).

Uses `asyncio.gather()` with `sqlite_session_factory` for concurrent DB access.

---

### Group 11: Health endpoint degradation

**Files: `tests/unit/infrastructure/test_health_degradation.py`**

Test `EventingHealthCheck` from `src/messaging/infrastructure/health/checkers.py`:
- Test with `pending_count=0` → status `"ok"`
- Test with `pending_count=10`, `oldest_age=300.0` → status `"degraded"`
- Test with `pending_count=100`, `oldest_age=3600.0` → status `"degraded"` (or `"unavailable"`)
- Test status transitions: add events to repository, assert health reflects backlog
- Test degradation curve: varying pending_count maps to correct status

Uses `FakeRepository` from `tests/unit/infrastructure/conftest.py`.
