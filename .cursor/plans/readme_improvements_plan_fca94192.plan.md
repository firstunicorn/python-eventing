---
name: README improvements plan
overview: Comprehensive README improvements including installation instructions, clarifying package/import naming confusion, adding TOC, setup guide, scope clarification, decision criteria, comparison context, and troubleshooting documentation.
todos: []
isProject: false
---

# README improvement implementation plan

## Critical context discovered

**Package naming clarification (CRITICAL):**
- PyPI distribution name: `python-eventing`
- Python import package: `messaging` (NOT `eventing`)
- Current README examples are CORRECT (use `messaging.*`)
- Lines 141-143 incorrectly state import package is `eventing`

**Evidence:**
- [`pyproject.toml`](pyproject.toml) line 9: `packages = [{include = "messaging", from = "src"}]`
- All source code uses `from messaging ...` imports
- [`docs/source/integration-guide.md`](docs/source/integration-guide.md) line 17 also has same error

## Changes to README.md

### 1. Add installation section (after line 12)

**Location:** After documentation link, before support scale table

**Content structure:**
```markdown
## Installation

```bash
pip install python-eventing
# or
poetry add python-eventing
```

**Import package name:** `messaging` (distribution is `python-eventing`)

```python
from messaging.core import BaseEvent
from messaging.infrastructure import SqlAlchemyOutboxRepository
```

**Requirements:**
- Python 3.12+
- PostgreSQL (outbox persistence)
- Kafka Connect with Debezium CDC (publishing infrastructure)
```

**Rationale:** Addresses blocking issue for first-time users, clarifies package/import name confusion immediately

### 2. Add table of contents (after badges, before support scale line)

**Location:** After line 8 (badges), before line 14 (support scale note)

**Content:**
```markdown
## Table of contents

- [Installation](#installation)
- [When to use this package](#when-to-use-this-package)
- [Comparison with alternatives](#comparison-with-alternatives)
- [Scope](#scope)
- [Quick start: transactional outbox](#quick-start-transactional-outbox)
- [Setup](#setup)
- [Advanced: EventBus](#advanced-eventbus-optional)
- [Documentation](#documentation)
- [Local development](#local-development)
```

**Rationale:** Improves navigation for 155-line file

### 3. Add "When to use this package" section (before comparison table)

**Location:** After TOC, before support scale line (currently line 14)

**Content:**
```markdown
## When to use this package

**Use `python-eventing` if you need:**
- Guaranteed event delivery via transactional outbox pattern
- Kafka-based microservice messaging with CDC publishing
- Dead letter queue handling with database bookkeeping
- Idempotent consumer patterns with durable deduplication
- Native broker integration (FastStream, Debezium CDC, RabbitMQ DLX)

**Consider alternatives if:**
- Simple in-process events only → [`pyventus`](https://github.com/mdapena/pyventus)
- FastAPI request-scoped events → [`fastapi-events`](https://github.com/melvinkcx/fastapi-events)
- Non-Kafka message brokers without CDC support
- No need for durable outbox persistence
```

**Rationale:** Helps developers self-select correct tool, prevents wrong-tool-for-job issues

### 4. Add comparison table introduction (before table)

**Location:** Before comparison table (currently line 16)

**Content:**
```markdown
## Comparison with alternatives

`python-eventing` prioritizes **durable messaging** (transactional outbox + CDC) and **Kafka/RabbitMQ integration** over in-process event simplicity:
```

**Rationale:** Provides context before front-loading complexity table

### 5. Add setup section (before Quick Start)

**Location:** After Scope section, before Quick Start (currently line 59)

**Content:**
```markdown
## Setup

### Database schema

The outbox table stores events transactionally with your business data:

```sql
CREATE TABLE outbox_events (
    event_id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(255) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    published BOOLEAN DEFAULT FALSE NOT NULL,
    failed BOOLEAN DEFAULT FALSE NOT NULL,
    attempt_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE INDEX idx_outbox_unpublished ON outbox_events (published, created_at);
```

### Application startup

Initialize the outbox repository and event bus at application startup:

```python
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from messaging.infrastructure import SqlAlchemyOutboxRepository
from messaging.core import build_event_bus

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Database engine
    engine = create_async_engine("postgresql+asyncpg://...")

    # Outbox repository
    outbox_repo = SqlAlchemyOutboxRepository(engine)
    app.state.outbox_repository = outbox_repo

    # Optional: EventBus for advanced patterns
    event_bus = build_event_bus()
    app.state.event_bus = event_bus
```

**CDC Publishing:** Kafka Connect with Debezium CDC automatically detects outbox table changes and publishes to Kafka. See [`debezium-cdc-architecture.md`](https://python-eventing.readthedocs.io/en/latest/debezium-cdc-architecture.html) for configuration.
```

**Schema source:** [`src/messaging/infrastructure/persistence/orm_models/outbox_orm.py`](src/messaging/infrastructure/persistence/orm_models/outbox_orm.py)

**Rationale:** Addresses missing prerequisite setup; Quick Start currently jumps to usage without initialization context

### 6. Expand Scope section with anti-scope

**Location:** Current Scope section (lines 34-41)

**Modification:** Add "NOT included" subsection

**Content addition:**
```markdown
## Scope

**Included:**
- Transactional outbox primitives (write-side only; CDC handles publishing)
- Event contracts and registry
- Kafka/RabbitMQ consumer base classes with idempotency
- Native broker integration (Kafka Connect CDC, RabbitMQ DLX, FastStream middlewares)
- In-process emitter/subscriber facade and hooks
- DLQ bookkeeping consumer for database flag synchronization

**NOT included (delegated to external systems):**
- Event publishing (handled by Kafka Connect with Debezium CDC)
- Message broker infrastructure setup (use official Kafka/RabbitMQ documentation)
- Schema registry management (use Confluent Schema Registry or alternatives)
- Request-scoped FastAPI event middleware (intentionally avoided)
- Consumer batch handling (use `fastapi-events` if needed)
```

**Rationale:** Sets clear boundaries, prevents users from expecting features handled elsewhere

### 7. Fix Distribution section (lines 141-143)

**Current (INCORRECT):**
```markdown
- PyPI distribution name: `python-eventing`
- Python import package: `eventing`
```

**Fix to:**
```markdown
## Distribution

- PyPI distribution name: `python-eventing`
- Python import package: `messaging`

```python
# Install
pip install python-eventing

# Import
from messaging.core import BaseEvent
from messaging.infrastructure import SqlAlchemyOutboxRepository
```

Services should consume the published package rather than source checkout. Kafka remains shared infrastructure with local producer/consumer clients per service.
```

**Rationale:** Corrects critical confusion between distribution name and import name

## Changes to Sphinx documentation

### Create troubleshooting.md

**Location:** [`docs/source/troubleshooting.md`](docs/source/troubleshooting.md) (new file)

**Content structure:**
```markdown
# Troubleshooting

Common issues and solutions for `python-eventing` integration.

## Events stuck in outbox (not publishing)

**Symptoms:**
- Events persist to `outbox_events` table
- `published` flag remains `false`
- No events appearing in Kafka topics

**Solutions:**
1. Verify Kafka Connect Debezium connector is running:
   ```bash
   curl http://localhost:8083/connectors/outbox-connector/status
   ```

2. Check CDC connector configuration points to outbox table:
   ```json
   {
     "table.include.list": "public.outbox_events",
     "transforms": "outbox",
     "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter"
   }
   ```

3. Review Kafka Connect logs for CDC errors:
   ```bash
   docker logs kafka-connect
   ```

4. Verify database permissions for Debezium user

## Duplicate messages consumed

**Symptoms:**
- Same event processed multiple times
- Idempotent consumer not preventing duplicates

**Solutions:**
1. Ensure `IProcessedMessageStore` is configured in consumer:
   ```python
   from messaging.infrastructure import IdempotentConsumerBase

   class MyConsumer(IdempotentConsumerBase):
       def __init__(self, store: IProcessedMessageStore):
           super().__init__(store)
   ```

2. Verify `processed_messages` table exists and is populated

3. Check consumer is using transactional session for store operations

4. Review Kafka consumer group configuration (enable.auto.commit=false)

## Health check failures

**Symptoms:**
- `/health` endpoint returns unhealthy status
- Outbox health check failing

**Solutions:**
1. Check outbox table has unpublished events older than threshold:
   ```sql
   SELECT COUNT(*) FROM outbox_events
   WHERE published = false
   AND created_at < NOW() - INTERVAL '5 minutes';
   ```

2. Verify Kafka Connect CDC is processing changes

3. Review FastStream broker health endpoint configuration

4. Check database connection pool exhaustion

## Import errors

**Symptom:**
```python
ModuleNotFoundError: No module named 'eventing'
```

**Solution:**
The import package is `messaging`, not `eventing`:
```python
# Correct
from messaging.core import BaseEvent

# Incorrect
from eventing.core import BaseEvent  # ❌
```

The PyPI distribution name is `python-eventing`, but imports use `messaging`.

## Performance issues

**Symptoms:**
- Slow outbox writes
- High database load

**Solutions:**
1. Add database indexes on outbox table (see Setup section)

2. Tune Debezium CDC polling interval:
   ```json
   {
     "poll.interval.ms": "500"
   }
   ```

3. Increase Kafka Connect worker threads

4. Review SQLAlchemy connection pool settings

5. Consider partitioning outbox table by created_at for high volume

## Further assistance

- Review [Integration Guide](integration-guide.html) for setup verification
- Check [Debezium CDC Architecture](debezium-cdc-architecture.html) for publishing details
- See [Consumer Transactions](consumer-transactions.html) for idempotency patterns
- Open issue on GitHub: https://github.com/firstunicorn/python-eventing/issues
```

### Update index.md toctree

**Location:** [`docs/source/index.md`](docs/source/index.md) line 10-23

**Add to toctree:**
```markdown
```{toctree}
:maxdepth: 2
:caption: Contents

event-catalog
integration-guide
broker-selection-guide
debezium-cdc-architecture
kafka-rabbitmq-features
cross-service-communication
transactional-outbox
dlq-handlers
consumer-transactions
troubleshooting
```
```

**Rationale:** Makes troubleshooting accessible from main documentation navigation

## Additional fix: integration-guide.md

**Location:** [`docs/source/integration-guide.md`](docs/source/integration-guide.md) line 17

**Current (INCORRECT):**
```markdown
The published distribution name is `python-eventing`, while Python imports stay
`from eventing ...`.
```

**Fix to:**
```markdown
The published distribution name is `python-eventing`, while Python imports use
`from messaging ...` (not `eventing`).
```

**Rationale:** Same critical naming confusion as README

## File modification summary

1. [`README.md`](README.md) - 8 structural additions/modifications
2. [`docs/source/troubleshooting.md`](docs/source/troubleshooting.md) - New file
3. [`docs/source/index.md`](docs/source/index.md) - Add troubleshooting to toctree
4. [`docs/source/integration-guide.md`](docs/source/integration-guide.md) - Fix import name

## Testing verification

After changes:
1. Verify README renders correctly on GitHub
2. Build Sphinx docs: `cd docs && make html`
3. Verify troubleshooting page appears in sidebar navigation
4. Check all internal links resolve correctly
5. Verify code examples are copy-pasteable

## Priority order

1. Fix Distribution section (lines 141-143) - Critical blocker
2. Add Installation section - Blocking for first-time users
3. Add Setup section - Missing prerequisite
4. Add TOC - Navigation improvement
5. Add "When to use" section - Decision criteria
6. Add comparison intro - Context clarity
7. Expand Scope - Boundary setting
8. Create troubleshooting.md - Self-service support
9. Fix integration-guide.md - Consistency