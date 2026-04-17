# Integration guide

Use the `python-eventing` package when a domain service needs both local
in-process dispatch and reliable cross-service publication.

**For detailed cross-service architecture:** See {doc}`cross-service-communication` for database isolation patterns, Kafka/RabbitMQ architecture, and production deployment examples.

## Install the package

Use a normal package dependency instead of a source checkout:

```toml
python-eventing = "^0.1.0"
```

The published distribution name is `python-eventing`, while Python imports stay
`from eventing ...`.

## Add a new event schema

1. Create a Pydantic event model that extends
   `eventing.core.contracts.BaseEvent`.
2. Declare a stable default `event_type` so the registry can auto-register it.
3. Keep payload fields transport-safe and JSON-serializable.

For trusted backend integrations, model the event as a fact. Send stable
business identifiers, timestamps, correlation ids, and metadata only. Do not
encode downstream reward outcomes such as XP amounts or streak changes in the
producer payload.

## Register and dispatch

1. Register the event class in an `EventRegistry`.
2. Add dispatcher registrations through
   `eventing.core.contracts.build_dispatcher` or the higher-level
   `eventing.core.contracts.build_event_bus`.
3. Include the outbox writer handler so in-process dispatch automatically
   persists the event inside the same application transaction.

The higher-level `EventBus` also exposes decorator registration, pluggable
dispatch backends, success/failure/global hooks, and tracing/debug/disable
hooks while keeping the current outbox and Kafka data plane unchanged.

## Publish through the outbox

1. Persist the domain event with
   `eventing.infrastructure.outbox.OutboxEventHandler`.
2. Let `eventing.infrastructure.outbox.OutboxWorker` read unpublished rows.
3. Publish via `eventing.infrastructure.messaging.KafkaEventPublisher`.
4. Route terminal failures through
   `eventing.infrastructure.messaging.DeadLetterHandler`.

## Consume idempotently

Create inbound consumers by extending
`eventing.infrastructure.messaging.IdempotentConsumerBase`. This keeps
cross-service handlers small and ensures replay-safe event handling when Kafka
redelivers a message.

Keep producer-specific translation at the consuming service boundary. For
example, gamification extensions can map `learning.lesson.completed` into
`RecordTrustedActivity` without teaching the eventing service about lesson or
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
