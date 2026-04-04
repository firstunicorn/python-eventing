---
name: Move extracted files to subfolders
overview: Rename messaging/infrastructure/messaging/ to messaging/infrastructure/pubsub/, then move 3 groups of split files into subfolders and update all imports via Serena MCP.
todos:
  - id: rename-messaging-to-pubsub
    content: Rename messaging/infrastructure/messaging/ to messaging/infrastructure/pubsub/
    status: in_progress
  - id: init-consumer-base
    content: Create __init__.py for consumer_base/ with re-exports
    status: pending
  - id: move-consumer-siblings
    content: Move consumer_helpers.py, consumer_validators.py, consumer_consume.py to consumer_base/
    status: pending
  - id: move-kafka-consumer
    content: Move kafka_consumer_base.py into consumer_base/
    status: pending
  - id: init-processed-msg-store
    content: Create __init__.py for processed_message_store/ with re-exports
    status: pending
  - id: move-claim-siblings
    content: Move claim_helpers.py, claim_statement_builder.py, duplicate_checker.py to processed_message_store/
    status: pending
  - id: move-processed-msg-store
    content: Move processed_message_store.py into processed_message_store/
    status: pending
  - id: init-orm-models
    content: Create __init__.py for orm_models/ with re-exports
    status: pending
  - id: move-orm-files
    content: Move orm_base.py, outbox_orm.py, processed_message_orm.py to orm_models/
    status: pending
  - id: serena-update-imports
    content: Activate Serena MCP and update all import paths across all files
    status: pending
  - id: run-lint-verify
    content: Run ruff check --fix and mypy src/ to verify all passes
    status: pending
isProject: false
---

## Phase 0: Rename `messaging/` → `pubsub/`

Rename `src/messaging/infrastructure/messaging/` to `src/messaging/infrastructure/pubsub/`.
New dotted import prefix: `messaging.infrastructure.pubsub.*`

13 files at this directory level. References in 13 source files project-wide.

## Phase 1: `consumer_base/` (inside `pubsub/`)

**Location:** `src/messaging/infrastructure/pubsub/consumer_base/`

Move into this folder:
- `consumer_helpers.py`
- `consumer_validators.py`
- `consumer_consume.py`
- `kafka_consumer_base.py` (parent file)

**Resulting structure:**
```
infrastructure/pubsub/
├── consumer_base/
│   ├── __init__.py        # re-export IdempotentConsumerBase + helpers
│   ├── kafka_consumer_base.py
│   ├── consumer_consume.py
│   ├── consumer_helpers.py
│   └── consumer_validators.py
├── ...
```

## Phase 2: `processed_message_store/` (inside `persistence/`)

**Location:** `src/messaging/infrastructure/persistence/processed_message_store/`

Move into this folder:
- `claim_helpers.py`
- `claim_statement_builder.py`
- `duplicate_checker.py`
- `processed_message_store.py` (parent file, 93 lines)

**Resulting structure:**
```
infrastructure/persistence/
├── processed_message_store/
│   ├── __init__.py        # re-export SqlAlchemyProcessedMessageStore + helpers
│   ├── processed_message_store.py
│   ├── claim_helpers.py
│   ├── claim_statement_builder.py
│   └── duplicate_checker.py
├── orm_models/
├── session.py
├── __init__.py
```

## Phase 3: `orm_models/` (inside `persistence/`)

**Location:** `src/messaging/infrastructure/persistence/orm_models/`

Move into this folder:
- `orm_base.py`
- `outbox_orm.py`
- `processed_message_orm.py`

**Resulting structure:**
```
infrastructure/persistence/
├── orm_models/
│   ├── __init__.py        # re-export ORM model classes
│   ├── orm_base.py
│   ├── outbox_orm.py
│   └── processed_message_orm.py
├── processed_message_store/
├── session.py
├── __init__.py
```

### Execution steps

1. **Rename** `infrastructure/messaging/` → `infrastructure/pubsub/`.

2. **Create 3 `__init__.py` files** in each new subfolder with module docstrings + re-exports.

3. **Move files using `Move` tool** (NOT Write + Delete):
   - Phase 1 (consumer_base): 4 moves
   - Phase 2 (processed_message_store): 4 moves
   - Phase 3 (orm_models): 3 moves

4. **Activate Serena MCP** with `activate_project`, then update all imports:
   - `find_referencing_symbols` on each moved/renamed module
   - Rewrite all import paths project-wide

5. **Run `ruff check --fix`** + **`mypy src/`** to verify.

### Files staying at parent level (not into subfolders)
- `infrastructure/pubsub/broker_config.py`, `dead_letter_handler.py`, `kafka_publisher.py`, `processed_message_store.py` (protocol) — public API modules
- `infrastructure/persistence/session.py` — independent

### Import path changes (examples)
| Old | New |
|-----|-----|
| `from messaging.infrastructure.messaging.consumer_helpers import ...` | `from messaging.infrastructure.pubsub.consumer_base.consumer_helpers import ...` |
| `from messaging.infrastructure.messaging.kafka_consumer_base import ...` | `from messaging.infrastructure.pubsub.consumer_base.kafka_consumer_base import ...` |
| `from messaging.infrastructure.persistence.claim_helpers import ...` | `from messaging.infrastructure.persistence.processed_message_store.claim_helpers import ...` |
| `from messaging.infrastructure.persistence.outbox_orm import ...` | `from messaging.infrastructure.persistence.orm_models.outbox_orm import ...` |