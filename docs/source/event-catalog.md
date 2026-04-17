# Event catalog

The canonical event contract is defined by the installable `eventing` import
package via `eventing.core.contracts.BaseEvent`.
Every published event shares the fields below before service-specific payload
fields are added.

| Field | Purpose |
| --- | --- |
| `eventId` | Stable event identity used for deduplication and tracing. |
| `eventType` | Logical schema name such as `gamification.xp.awarded`. |
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

## Event type and source validation

### Format rules (Layer 1)

**Event type format:** `domain.entity.event`
- Must have exactly 3 segments separated by dots
- All lowercase letters only
- Example: `gamification.xp.awarded`, `orders.order.created`
- Invalid: `gamification.XPAwarded` (PascalCase), `test.event` (only 2 segments)

**Source format:** `service-name`
- Must start with lowercase letter
- Followed by lowercase letters, numbers, or hyphens
- Example: `gamification-service`, `order-service-v2`
- Invalid: `GamificationService` (uppercase), `2nd-service` (starts with number)

### Optional catalog validation (Layer 2)

Organizations can optionally configure an external Git repository as a centralized
event catalog. When configured via `EVENT_CATALOG_REPO_URL`, the library validates
events and services against TOML registries:

**Environment variables:**
- `EVENT_CATALOG_REPO_URL`: Git repository URL (e.g., `https://github.com/org/event-catalog`)
- `EVENT_CATALOG_BRANCH`: Branch to use (default: `main`)
- `EVENT_CATALOG_STRICT_MODE`: `true` to reject unregistered events, `false` to warn only (default: `false`)
- `EVENT_CATALOG_REFRESH_INTERVAL`: Cache refresh interval in seconds (default: `3600`)
- `EVENT_CATALOG_LOCAL_PATH`: Local cache directory (default: `./.event-catalog`)

**Your organization's catalog repository structure:**

This is the structure for your own centralized event catalog Git repository (not part of the `python-eventing` library):

```
your-event-catalog/
├── events.toml      # Event registry
├── services.toml    # Service registry
└── schemas/         # Optional JSON Schemas
    └── *.schema.json
```

**Example `events.toml` in your catalog:**
```toml
[events."orders.order.created"]
owner_service = "order-service"
owner_team = "commerce"
description = "Emitted when a new order is placed"
```

**Example `services.toml` in your catalog:**
```toml
[services.order-service]
team = "commerce"
repository = "https://github.com/your-org/order-service"
events_published = ["orders.order.created"]
```

## Published domain event examples

> **Note:** The events below are purely illustrative examples. The `python-eventing` library does *not* contain any hardcoded business payloads or domains (like gamification).

The eventing service does not define producer-specific business payloads.
Instead, it provides the reusable base contract that other services extend. The
rows below show how a theoretical gamification service might structure its domain
events using that shared contract.

| Event type | Producer | Payload fields |
| --- | --- | --- |
| `gamification.xp.awarded` | `gamification-service` | `userId`, `amount`, `sourceActivity` |
| `gamification.level.achieved` | `gamification-service` | `userId`, `oldLevel`, `newLevel` |
| `gamification.streak.updated` | `gamification-service` | `userId`, `streakDays`, `action` |

## Trusted backend fact examples

> **Note:** Similarly, these are purely theoretical examples of how other microservices might use the eventing contracts.

Producer services can also publish facts for downstream consumers without
embedding reward decisions in the payload. These events still use the shared
base fields from `BaseEvent`, but their payloads stay facts-only.

| Event type | Producer | Payload intent |
| --- | --- | --- |
| `learning.lesson.completed` | `learning-service` | A lesson was completed by a user. |
| `assessment.quiz.completed` | `assessment-service` | A quiz was completed by a user. |
| `identity.user.registered` | `identity-service` | A new user profile was created. |

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
