# Plan for Removing/Simplifying Code Native to FastStream

> **STATUS: INCORPORATED** - The removals and simplifications outlined here have been fully integrated into the main feature plan (`add_eventing_features_12bad60a.plan.md`) under Phase 0.5.

Based on a deep analysis of the `python-eventing` codebase, the full FastStream documentation, and your universal broker-agnostic architecture principles, here is the plan for removing redundant code and simplifying the system.

## What MUST Stay (Broker-Agnostic Core)
As discussed, we will **NOT** remove the custom `ScheduledOutboxWorker` or the `DeadLetterHandler`. These are core to your "Package-first universal eventing infrastructure" (as defined in `llms-full.txt`) and cannot be replaced by Debezium/Native DLX without introducing tight coupling and external infrastructure dependencies.

Similarly, the `EventBus` (in `messaging.core.contracts.bus`) is for **local in-process dispatch** (Domain -> Outbox) and must stay, as FastStream is designed for cross-service broker dispatch, not local aggregate event emission.

## What WILL Be Removed / Simplified

### 1. Remove `EventRegistry` Overhead in the Outbox Path
**Current State:** When `ScheduledOutboxWorker` polls the database, `OutboxQueryOperations` queries the JSON payload and uses `EventRegistry.deserialize(record.payload)` to convert it back into a full Pydantic `BaseEvent` model. Immediately after, `KafkaEventPublisher` converts it *back* to a dictionary via `.to_message()` to publish to Kafka.
**Native FastStream Coverage:** FastStream's `KafkaBroker.publish()` natively accepts Python dictionaries (which it serializes to JSON).
**Action:** 
- Modify `OutboxQueryOperations.get_unpublished` to yield a lightweight wrapper (e.g., `RawOutboxEvent`) that holds the raw `dict[str, Any]` parsed from the database.
- Completely remove the `EventRegistry` dependency from `SqlAlchemyOutboxRepository` and `OutboxQueryOperations`.
- **Result:** Massive performance boost by eliminating the `JSON -> Pydantic Model -> Dict -> JSON` roundtrip during outbox publishing.

### 2. Remove Custom Observability Hooks
**Current State:** We had planned and written initial tests for custom `create_kafka_telemetry` and Prometheus hooks.
**Native FastStream Coverage:** FastStream officially provides `KafkaPrometheusMiddleware` and `KafkaTelemetryMiddleware`.
**Action:**
- Delete the custom hook stubs in `tests/unit/observability/`.
- Directly import and use FastStream's native middlewares in `create_kafka_broker` inside `broker_config.py`.

### 3. Simplify Health Checks (`check_broker`)
**Current State:** `checkers.py` has a `check_broker` function that manually calls `await broker.ping(1.0)`.
**Native FastStream Coverage:** FastStream provides a native ASGI wrapper `make_ping_asgi` for liveness/readiness probes.
**Action:**
- While we keep `EventingHealthCheck` for aggregating DB/Lag/Broker health into a single JSON payload, we can expose the broker ping natively if we mount FastStream into FastAPI using `AsgiFastStream`. We will remove manual ping loops in favor of leveraging FastStream's lifecycle and `broker.ping()` directly within the aggregated check without custom error wrapping.

### 4. Remove Manual Consumer Deserialization 
**Current State:** Our `IdempotentConsumerBase` accepts `message: dict[str, Any]` and extracts `event_id` manually.
**Native FastStream Coverage:** FastStream automatically validates and deserializes incoming JSON directly into Pydantic models when you type-hint the subscriber: `@broker.subscriber("topic") async def handle(event: MyEventModel)`.
**Action:**
- Update consumer documentation/examples to show that downstream services should rely entirely on FastStream's native Pydantic injection, rather than manually deserializing dictionaries using our `EventRegistry`. The `EventRegistry` is only needed internally if dealing with polymorphic raw dicts, but FastStream handles routing natively.

---

## What we verified DOES NOT exist natively in FastStream (Requires Custom Code):
- **Rate Limiting & Circuit Breaker:** FastStream docs explicitly state these should be implemented via the `consume_scope` middleware. There are no built-in plugins for this. Our plan to use `aiolimiter` and a custom circuit breaker is correct.
- **Consumer Idempotency Store:** FastStream provides at-least-once (ACK) delivery but no persistent DB-backed deduplication. Our `IdempotentConsumerBase` + `ProcessedMessageStore` is required.
- **Schema Registry Validation:** FastStream supports Avro via Confluent Kafka, but for JSON payloads, it relies on standard Pydantic. Our custom JSON Schema Registry with `data_version` evolution checks is required.

Shall I update the master plan `.cursor/plans/add_comprehensive_eventing_tests_12bad60a.plan.md` to reflect these exact removals and simplifications before continuing with Phase 0 (Tests)?