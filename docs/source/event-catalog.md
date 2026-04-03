# Event catalog

The canonical event contract is defined by the installable `eventing` import
package via `eventing.core.contracts.BaseEvent`.
Every published event shares the fields below before service-specific payload
fields are added.

| Field | Purpose |
| --- | --- |
| `eventId` | Stable event identity used for deduplication and tracing. |
| `eventType` | Logical schema name such as `gamification.XPAwarded`. |
| `aggregateId` | Aggregate or entity identity that the event belongs to. |
| `occurredAt` | UTC timestamp for when the event was produced. |
| `source` | Producing service identifier. |
| `dataVersion` | Schema version for consumer compatibility checks. |
| `correlationId` | Request or workflow correlation token. |
| `causationId` | Parent event or command identity. |
| `metadata` | Extra transport-safe attributes. |

The transport envelope is produced through
`eventing.core.contracts.EventEnvelopeFormatter`, which wraps each event as a
CloudEvents 1.0 payload before publication.

## Published domain event examples

> **Note:** The events below are purely illustrative examples. The `python-eventing` library does *not* contain any hardcoded business payloads or domains (like gamification).

The eventing service does not define producer-specific business payloads.
Instead, it provides the reusable base contract that other services extend. The
rows below show how a theoretical gamification service might structure its domain
events using that shared contract.

| Event type | Producer | Payload fields |
| --- | --- | --- |
| `gamification.XPAwarded` | `gamification-service` | `userId`, `amount`, `sourceActivity` |
| `gamification.LevelUpAchieved` | `gamification-service` | `userId`, `oldLevel`, `newLevel` |
| `gamification.StreakUpdated` | `gamification-service` | `userId`, `streakDays`, `action` |

## Trusted backend fact examples

> **Note:** Similarly, these are purely theoretical examples of how other microservices might use the eventing contracts.

Producer services can also publish facts for downstream consumers without
embedding reward decisions in the payload. These events still use the shared
base fields from `BaseEvent`, but their payloads stay facts-only.

| Event type | Producer | Payload intent |
| --- | --- | --- |
| `learning.lesson_completed` | `learning-service` | A lesson was completed by a user. |
| `assessment.quiz_completed` | `assessment-service` | A quiz was completed by a user. |
| `identity.user_registered` | `identity-service` | A new user profile was created. |

Facts-only means producers send stable identifiers, timestamps, and transport
metadata. They do not send XP amounts, streak deltas, or level changes. Those
effects are computed by the consuming domain service.

## Storage contract

The outbox table persists:

- the canonical `eventType`
- the `aggregateId`
- the serialized event payload
- timestamps and publication bookkeeping

That persistence format is implemented by
`eventing.infrastructure.outbox.SqlAlchemyOutboxRepository` and the
`eventing.infrastructure.persistence.OutboxRecord` ORM model.
