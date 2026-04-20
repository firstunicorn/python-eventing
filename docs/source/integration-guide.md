# Integration guide

Use the `messagekit` package when a domain service needs both local
in-process dispatch and reliable cross-service publication.

**For detailed cross-service architecture:** See {doc}`cross-service-communication` for database isolation patterns, Kafka/RabbitMQ architecture, and production deployment examples.

## Install the package

Add to your project's `pyproject.toml`:

```toml
[tool.poetry.dependencies]
python = "^3.12"
messagekit = "^0.1.0"
```

Or install directly:

```bash
pip install messagekit
# or
poetry add messagekit
```

The distribution and import name is `messagekit`:

## Add a new event schema

1. Create a Pydantic event model that extends
   `messagekit.core.BaseEvent`.
2. Declare a stable default `event_type` so the registry can auto-register it.
3. Keep payload fields transport-safe and JSON-serializable.

For trusted backend integrations, model the event as a fact. Send stable
business identifiers, timestamps, correlation ids, and metadata only. Do not
encode downstream reward outcomes such as XP amounts or streak changes in the
producer payload.

## Register and dispatch

1. Register the event class in an `EventRegistry`.
2. Add dispatcher registrations through
   `messagekit.core.build_dispatcher` or the higher-level
   `messagekit.core.build_event_bus`.
3. Include the outbox writer handler so in-process dispatch automatically
   persists the event inside the same application transaction.

The higher-level `EventBus` also exposes decorator registration, pluggable
dispatch backends, success/failure/global hooks, and tracing/debug/disable
hooks while keeping the current outbox and Kafka data plane unchanged.

## Publish through the outbox

1. Persist the domain event with
   `messagekit.infrastructure.OutboxEventHandler`.
2. Kafka Connect with Debezium CDC automatically monitors the outbox table and
   publishes to Kafka (no manual polling needed).
3. Configure CDC with the Outbox Event Router SMT to route events to topics
   based on event type.

See {doc}`debezium-cdc-architecture` for CDC connector configuration details.

## Consume idempotently

Create inbound consumers by extending
`messagekit.infrastructure.IdempotentConsumerBase`. This keeps
cross-service handlers small and ensures replay-safe event handling when Kafka
redelivers a message.

Keep producer-specific translation at the consuming service boundary. For
example, gamification extensions can map `learning.lesson.completed` into
`RecordTrustedActivity` without teaching the messagekit library about lesson or
quiz reward logic.

## Optional later extension

If the platform later needs replay tooling, DLQ inspection, or event-catalog
operations, add a small Eventing ops/admin service. Keep it off the hot path:
services still publish locally through the package, their own outbox, and Kafka.

## Topic convention

Use stable namespaced topic names following the `domain.entity.event` pattern (all lowercase), for example `gamification.xp.awarded`,
`learning.lesson.completed`, or `assessment.quiz.completed`. The Kafka
publisher resolves the topic name from the event payload so producers do not
need a separate topic map for standard cases.
