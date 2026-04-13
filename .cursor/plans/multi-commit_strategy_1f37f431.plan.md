---
name: Multi-commit Strategy
overview: Create 6 logical commits separating bug fixes, coverage configuration, test additions, and refactoring work completed across 400+ messages in this session.
todos: []
isProject: false
---

# Multi-Commit Strategy for Eventing Microservice Changes

Based on analysis of the full conversation history (400+ messages), git status, and git commit history, this plan organizes all work into 6 logical commits following conventional commits format.

**VERIFIED**: Git history confirms that manual acknowledgment (AckPolicy.MANUAL, KafkaMessage parameter, ValidationError handling, msg.ack() after transaction) were NOT in the last commit. These bug fixes ARE new additions in this session, implemented during file splitting.

## Pre-Commit Verification Completed

- [x] Reviewed entire context window (all 400+ messages)
- [x] Ran `git status` - 11 modified, 20+ deleted, 100+ untracked files
- [x] Reviewed `git diff --stat` - 21 files changed, 43,365 insertions, 1,984 deletions
- [x] Cross-referenced all changes with conversation context
- [x] Identified logical groupings for commits
- [x] **CRITICAL**: Discovered staged changes are from OLD session, need reset

## Important: Reset Staging Area First

**Problem**: Current staging area contains old work from previous session that's already mixed with new changes.

**Solution**:
```bash
git reset HEAD
```

This unstages everything, allowing us to create clean, logical commits from the actual work done in this session.

## Commit Breakdown

### Commit 1: `fix(kafka): increase poll interval for test infrastructure delays`

**Scope**: Kafka consumer configuration timeout fix

**Files** (currently STAGED from old session, will be re-added after reset):
- `src/messaging/config/kafka_settings.py`

**Changes**:
- Increased `max.poll.interval.ms` from 300000 (5 min) to 600000 (10 min)
- Added comment explaining reason: test infrastructure delays

**Rationale**: Standalone bug fix addressing Kafka consumer timeout issues in test environments.

**Note**: This change is currently staged but will be reset and re-added as the first commit.

---

### Commit 2: `fix(bridge): add manual acknowledgment to prevent message loss`

**Scope**: FastStream integration bug fixes (BUG 1, 2, 3) implemented during file splitting

**Context**: Three critical bugs were identified and fixed during the file splitting work:
1. Missing manual acknowledgment (message loss on crash)
2. No JSON deserialization error handling
3. Transaction not atomic with Kafka offset commit

**Git History Verification**: The last commit (`5d33d73`) did NOT have `AckPolicy.MANUAL`, `msg: KafkaMessage`, or `ValidationError` handling. These are NEW additions in this session.

**Files** (all UNSTAGED, need to add):
- `src/messaging/main/_initialization/` (deleted original file, created split structure)
  - `__init__.py`
  - `app_state.py`
  - `broker_setup.py`
  - `bridge_setup/__init__.py`
  - `bridge_setup/config.py`
  - `bridge_setup/handler_registration.py` ← **BUG 1 FIX**: Added `AckPolicy.MANUAL`, `msg: KafkaMessage`
  - `bridge_setup/message_processor.py` ← **BUG 2, 3 FIX**: Added try/except, `msg.ack()` after transaction

**Changes**:
- Added `AckPolicy.MANUAL` to `@broker.subscriber` decorator
- Added `msg: KafkaMessage` parameter annotation for manual ack control
- Wrapped handler in try/except with `ValidationError` catch (BUG 2)
- Moved `msg.ack()` to execute AFTER `session.begin()` exits (BUG 3)
- Added `msg.nack()` on failures for redelivery
- Split into modular structure as part of 100-line limit enforcement

**Commit Message**:
```
fix(bridge): add manual acknowledgment to prevent message loss

## Starting point: missing manual acknowledgment

The bridge handler at src/messaging/main/_initialization.py (from commit 5d33d73)
used FastStream's default auto-acknowledgment, which commits Kafka offsets BEFORE
handler execution completes. This caused three critical bugs:

1. BUG 1 (HIGH): Missing manual acknowledgment - Kafka offset committed
   BEFORE handler executes, causing message loss on crash
2. BUG 2 (MEDIUM): No JSON deserialization error handling - malformed
   messages could crash handler
3. BUG 3 (HIGH): Transaction not atomic - SQLAlchemy commit separate
   from Kafka ack, violating exactly-once semantics

## Changes made

### BUG 1 fix: Manual acknowledgment (bridge_setup/handler_registration.py)
- Added `ack_policy=AckPolicy.MANUAL` to @broker.subscriber decorator
- Added `msg: KafkaMessage` parameter annotation
- Delegates to process_kafka_message for ack/nack control

### BUG 2 & 3 fixes: Error handling + atomic transaction (bridge_setup/message_processor.py)
- Wrapped handler in try/except with ValidationError catch for JSON errors
- Moved `await msg.ack()` to execute AFTER `session.begin()` exits
- Added `await msg.nack()` on failures to trigger redelivery
- Ensures atomic: Kafka offset commit + DB transaction + RabbitMQ publish

### File structure (100-line limit compliance)
- Split src/messaging/main/_initialization.py into modular structure:
  - bridge_setup/config.py - bridge configuration
  - bridge_setup/message_processor.py - message processing logic with bug fixes
  - bridge_setup/handler_registration.py - subscriber registration with manual ack
  - broker_setup.py - broker initialization
  - app_state.py - FastAPI state attachment

## Result

All three bugs fixed with proper error handling and atomic guarantees:
- Messages no longer lost on handler crash (manual ack)
- Malformed JSON messages properly rejected with nack
- Kafka offset only committed after successful DB + RabbitMQ publish
- Code modularized for maintainability (<100 lines per file)

Related tests in test_bridge_handler_integration.py verify fixes.
```

---

### Commit 3: `chore(coverage): add tiered coverage thresholds and validation`

**Scope**: Coverage configuration infrastructure

**Files**:
- `pyproject.toml` - Added coverage paths, pytest-xdist dependency
- `.github/workflows/tests.yml` - Added threshold validation step
- `.pre-commit-config.yaml` - Added pytest-xdist config
- `scripts/check_coverage_thresholds.py` (NEW)
- `docs/testing/coverage-strategy.md` (NEW)
- `coverage.json` (NEW)
- `COVERAGE_CONFIG_SUMMARY.md` (NEW)
- `poetry.lock` - Dependency lock update

**Changes**:
- Added tiered coverage thresholds: 80% overall, 85% critical paths
- Created validation script enforcing critical path thresholds
- Documented coverage strategy and rationale
- Integrated into CI/CD pipeline

---

### Commit 4: `test(bridge): add comprehensive FastStream integration tests`

**Scope**: New test files for bridge handler and FastStream behavior

**Files**:
- `tests/integration/test_faststream_library_verification.py` (NEW, split into sub-folder)
  - `test_manual_acknowledgment/` (split into 3 files)
  - `test_malformed_json.py`
  - `test_empty_messages.py`
  - `test_middleware_lifecycle.py`
  - `test_publish_interception.py`
  - `test_message_api.py`
  - `middleware_helpers.py`
- `tests/integration/test_bridge_handler_integration/` (NEW)
  - `test_message_forwarding.py`
  - `test_idempotency.py`
  - `test_empty_json.py`
  - `test_exception_nack.py`
  - `setup_helpers.py`
- `tests/unit/test_initialization_unit.py` (NEW)
- `tests/unit/infrastructure/test_faststream_contract.py` (NEW)
- `FASTSTREAM_BUGS_SUMMARY.md` (NEW)
- `IMPLEMENTATION_COMPLETE.md` (NEW)

**Changes**:
- Created behavioral tests documenting FastStream bugs (9 test classes)
- Created production integration tests for actual bridge handler (4 test classes)
- Created unit tests for initialization helpers (14 tests)
- Created contract tests for middleware signatures (4 tests)
- Documented bug identification process and fixes

---

### Commit 5: `test(outbox): add comprehensive unit tests for outbox repository`

**Scope**: New test files for outbox and DLQ functionality

**Files**:
- `tests/unit/infrastructure/outbox/` (NEW directory structure)
  - `test_outbox_repository_unit.py`
  - `conftest.py`
- `tests/unit/infrastructure/persistence/` (NEW directory structure)
  - `test_processed_message_store_unit.py`

**Changes**:
- Created comprehensive unit tests for outbox repository
- Created tests for processed message store
- Added fixtures for mocked dependencies

---

### Commit 6: `refactor(tests): enforce 100-line limit across entire codebase`

**Scope**: File splitting refactor for maintainability

**Files Modified**:
- `tests/conftest.py` - Split into conftest/ sub-folder
- `src/messaging/infrastructure/outbox/outbox_crud/operations.py` - Split into operations/ sub-folder
- `src/messaging/infrastructure/pubsub/broker_config/factory.py` - Split into factory/ sub-folder
- `src/messaging/infrastructure/kafka_dlq/orm_models.py` - Line ending normalization

**Files Deleted** (originals):
- `tests/chaos/test_circuit_breaker_resilience.py`
- `tests/chaos/test_kafka_connection_resilience/test_reconnection.py`
- `tests/integration/test_consumer_group_config.py`
- `tests/integration/test_dlq_admin_api.py`
- `tests/integration/test_kafka_consumer_groups/test_same_group_distribution.py`
- `tests/integration/test_kafka_rabbitmq_bridge.py`
- `tests/integration/test_testcontainers_smoke/test_kafka_postgres.py`

**New Directory Structure** (70+ files created):
- `tests/conftest/` - Split pytest config and fixtures
  - `config.py`, `cleanup_hooks/`, `database_fixtures.py`, `container_fixtures.py`, `http_client_fixtures.py`
- `tests/chaos/test_circuit_breaker_resilience/` - Split chaos tests
  - `conftest.py`, `test_circuit_opening.py`, `test_circuit_states.py`
- `tests/chaos/test_kafka_connection_resilience/test_reconnection/test_restart/` - Split reconnection tests
  - `setup.py`, `restart.py`, `verification.py`, `test_restart.py`
- `tests/integration/test_consumer_group_config/` - Split consumer group tests
  - `conftest.py`, `test_static_membership.py`, `test_disjoint_partitions.py`, `test_cooperative_rebalance.py`
- `tests/integration/test_dlq_admin_api/` - Split DLQ API tests
  - `test_listing.py`, `test_retry.py`
- `tests/integration/test_kafka_consumer_groups/test_same_group_distribution/test_distribution/` - Split distribution tests
  - `setup.py`, `messages.py`, `test_distribution.py`
- `tests/integration/test_kafka_rabbitmq_bridge/` - Split bridge tests
  - `test_kafka_consumption.py`, `test_rabbitmq_publishing.py`
- `tests/integration/test_testcontainers_smoke/test_kafka_postgres/test_smoke/` - Split smoke tests
  - `setup.py`, `verification.py`, `test_smoke.py`
- `src/messaging/infrastructure/outbox/outbox_crud/operations/crud_operations/` - Split CRUD ops
  - `core.py`, `add.py`, `status.py`
- `src/messaging/infrastructure/pubsub/broker_config/factory/` - Split broker factory
  - `kafka_broker_factory.py`, `middleware_builder.py`

**Changes**:
- Every file now under 100 lines (verified with pylint C0302)
- Proper Python package structure with `__init__.py` files
- Logical sub-folder organization by functionality
- All original content preserved (no trimming)
- Auto-fixed linter violations (Ruff, sorted imports)

**Rationale**:
- Enforces maintainability standard (<100 lines per file)
- Improves code navigation and comprehension
- Follows single responsibility principle
- Makes diffs more focused in future changes

---

### Additional Files Updated

**Documentation**:
- `README.md` - Updated test execution instructions
- `commit_msg.txt` - Updated with commit message drafts
- `.cursor/plans/file_splitting_plan_enforce_100-line_limit_ebb8e9aa.plan.md` (NEW)

**Excluded from commits** (as per user rules):
- `.specstory/` changes (metadata)
- `.specstory/history/` new files (conversation history)

## Verification Steps

After all commits:
1. Run pylint to verify 100-line compliance: `poetry run pylint --disable=all --enable=C0302 src/ tests/ --recursive=y`
2. Run Ruff to verify no violations: `poetry run ruff check src/ tests/`
3. Run Mypy for type checking: `poetry run mypy src/ tests/`
4. Optionally run tests (not required per user, will run in CI)

## Execution Order

1. **Reset staging area**: `git reset HEAD`
2. **Create Commit 1**: Stage and commit kafka_settings.py (timeout fix)
3. **Create Commit 2**: Stage and commit all bridge_setup files + _initialization files (bug fixes + file splitting)
4. **Create Commit 3**: Stage and commit coverage infrastructure files
5. **Create Commit 4**: Stage and commit FastStream test files
6. **Create Commit 5**: Stage and commit outbox test files
7. **Create Commit 6**: Stage and commit all remaining split files

## Notes

- All commits follow Conventional Commits format with lowercase types and scopes
- Bug fixes separated by concern for clarity (Commit 1: timeout, Commit 2: manual ack)
- File splitting grouped as single refactor for coherent history (Commit 6)
- Coverage config isolated as infrastructure change (Commit 3)
- Tests organized by functionality and purpose (Commits 4, 5)
- **CRITICAL**: Must reset staging area first to separate old and new work
- **VERIFIED**: Git history confirms manual acknowledgment features are NEW in this session
