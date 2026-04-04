---
name: Code verification plan
overview: Comprehensive verification of the eventing microservice against best practices documentation covering architecture, code quality, testing, outbox pattern implementation, and SOLID principles.
todos:
  - id: review-file-sizes
    content: Identify all files >100 lines and create refactoring plan for each (priority - split event_bus.py into HandlerResolver, DispatchExecutor, thin EventBus coordinator)
    status: completed
  - id: add-logging
    content: Add library logging (logging.getLogger with NullHandler only) to infrastructure, worker, repository, health checks
    status: completed
  - id: fix-outbox-transaction
    content: Refactor outbox repository to accept external session for true transactional outbox
    status: completed
  - id: add-dependencies
    content: Create FastAPI Depends() functions for database, outbox, health checks
    status: completed
  - id: fix-dip-violation
    content: Create universal DLQ handler (IEventPublisher interface) AND Kafka-specific DLQ handler (KafkaEventPublisher), keep explicitly separate
    status: completed
  - id: narrow-exceptions
    content: Replace broad Exception catches with specific exception types
    status: completed
  - id: clarify-consumer-transactions
    content: Document and enforce transaction boundaries in kafka_consumer_base
    status: completed
  - id: verify-tests
    content: Review test structure, run full test suite, verify property-based test profiles work
    status: completed
isProject: false
---

# Code verification against best practices

## Verification scope

This plan audits the eventing microservice (`c:\coding\gridflow-microservices-codex-taskmaster\microservices\eventing`) against the standards defined in `c:\coding\gridflow-microservices-codex-taskmaster\docs\initial\best-practices` and `c:\coding\gridflow-microservices-codex-taskmaster\docs\initial\architecture`.

## Critical context: This is a library, not an application

The `python-eventing` package is published to PyPI and imported by other services. This means:

**Libraries should**:
- Emit log messages using `logging.getLogger(__name__)`
- Add ONLY `NullHandler` to prevent "no handler" warnings
- Let consuming applications control log configuration

**Libraries must NEVER**:
- Call `logging.basicConfig()` or configure handlers/formatters
- Import and configure structlog/loguru
- Use print() statements
- Force logging preferences on applications

This distinction affects several findings below (especially section 2 on logging).

## Critical violations found

### 1. File size limits exceeded

**Standard**: Maximum 100 lines per file (75 lines ideal)
**Reference**: [COMMON BEST PRACTICES.md](c:\coding\gridflow-microservices-codex-taskmaster\docs\initial\best-practices\COMMON BEST PRACTICES.md) line 123

**Violations**:
- `src\eventing\infrastructure\outbox\outbox_repository.py`: 119 lines (has pylint disable comment)
- `src\eventing\core\contracts\bus\event_bus.py`: 101 lines
  - **Note**: This is a perfect candidate for splitting - it already violates SRP by mixing handler resolution, execution, error handling, and hooks in one class. Split into separate focused classes.
  - **Priority split** because it fixes both file size AND SRP violations
- `tests\unit\infrastructure\test_outbox_infrastructure.py`: 210 lines
- `tests\unit\test_main_and_routing.py`: 175 lines
- `tests\unit\core\test_event_bus.py`: 167 lines

**Splitting strategy for event_bus.py (101 lines → multiple files ≤75 lines each)**:
- Extract `HandlerResolver` class (handler name resolution, handler lookup)
- Extract `DispatchExecutor` class (actual handler invocation)
- Extract `DispatchHooks` to separate file (if not already separate)
- Keep thin `EventBus` as coordinator
- Each resulting file should be ≤75 lines

### 2. No logging (library pattern needed)

**Standard for libraries**: Libraries should emit logs using `logging.getLogger(__name__)` but NEVER configure logging (no basicConfig, no handlers except NullHandler, no formatters). Applications configure logging, not libraries.
**Reference**: Python logging best practices 2026 - libraries should log but not configure

**Current state**:
- Zero logging usage across entire `src\eventing` codebase
- Package `python-structlog-config` in dependencies (INCORRECT - this is for applications, not libraries)
- Should use standard library `logging` module with NullHandler only
- Operational insight missing for worker, health checks, repository operations
- Only exception: print() in docstring example at `core\__init__.py` lines 23-25

**Correct library logging pattern**:
```python
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())  # Only this handler!

# Then emit logs (application controls if/how they appear):
logger.debug("Polling outbox for unpublished events")
logger.info("Published %d events", len(batch))
logger.warning("Retry %d/%d for event %s", attempt, max_retries, event_id)
logger.error("Failed to connect to Kafka", exc_info=True)
```

**What libraries must NEVER do**:
- ❌ Call `logging.basicConfig()`
- ❌ Add StreamHandler, FileHandler, or any handler except NullHandler
- ❌ Configure formatters or log levels globally
- ❌ Import structlog/loguru and configure them
- ❌ Use print() statements

### 3. Transactional outbox pattern violation

**Standard**: Outbox events must be inserted in same transaction as business data
**Reference**: [06_EVENT_PATTERNS.md](c:\coding\gridflow-microservices-codex-taskmaster\docs\initial\architecture\06_EVENT_PATTERNS.md) lines 100-124

**Violations**:
- `outbox_repository.py` line 39: docstring says "without committing" but implementation commits immediately (line 43)
- Each `add_event()` opens new session and commits separately
- No way to share transaction with business logic (breaks atomicity guarantee)
- Pattern requires: `business_write + outbox_insert → single commit`, currently: `business_commit → outbox_commit` (dual write problem)

### 4. Missing FastAPI dependency injection

**Standard**: Use Depends() for database sessions, auth, services
**Reference**: [Code - Checklist - FastAPI.md](c:\coding\gridflow-microservices-codex-taskmaster\docs\initial\best-practices\FastAPI DEV detailed\EXAMPLES (DETAILED)\EXAMPLES (DETAILED)\code-quality\Code - Checklist - FastAPI.md) lines 49-64

**Violations**:
- Zero uses of `Depends()` in entire codebase
- `presentation\router.py` line 33: health endpoint accesses `request.app.state` directly instead of typed dependency
- No `get_db()` dependency pattern
- No dependency overrides for testing

### 5. SOLID principle violations

**Dependency Inversion Principle**:
- `dead_letter_handler.py` line 20: accepts concrete `KafkaEventPublisher` instead of `IEventPublisher` interface
- Worker uses interface (`outbox_worker.py` line 31) but DLQ handler doesn't (inconsistent)
- **Solution required**: Create TWO separate implementations, kept explicitly separate:

  **1. Universal DLQ handler** (`infrastructure/messaging/dead_letter_handler.py`):
  - Accepts `IEventPublisher` interface (broker-agnostic)
  - Works with any message broker (RabbitMQ, Kafka, Redis, NATS)
  - Primary implementation
  - Pure interface-based design

  **2. Kafka-specific DLQ handler** (`infrastructure/messaging/kafka/kafka_dead_letter_handler.py`):
  - Accepts `KafkaEventPublisher` concrete type
  - Can use Kafka-specific features (headers, partitions, timestamps, etc.)
  - Separate file, separate class
  - Optional enhancement when Kafka features are needed

  **Architecture**:
  - Keep implementations in different files/modules
  - Universal version should be the default/recommended
  - Kafka version can extend/wrap universal or be completely separate
  - Clear documentation on when to use each

**Single Responsibility**:
- `event_bus.py` mixes handler resolution, execution, error handling, hooks in one class (101 lines)
- This 101-line file is a perfect candidate for splitting (violates 100-line limit)
- Should be split into smaller, focused classes (see file size section below)

### 6. Broad exception handling

**Standard**: Catch specific exceptions, add context
**Reference**: [Code - Checklist - FastAPI.md](c:\coding\gridflow-microservices-codex-taskmaster\docs\initial\best-practices\FastAPI DEV detailed\EXAMPLES (DETAILED)\EXAMPLES (DETAILED)\code-quality\Code - Checklist - FastAPI.md) lines 150-166

**Violations**:
- `outbox_worker.py` line 69: `except Exception as exc` with minimal context
- `outbox_health_check.py` lines 65, 72: broad exception handlers
- `event_bus.py` line 76: catches all exceptions during dispatch

### 7. Consumer transaction management unclear

**Standard**: Database transactions must be explicit and scoped
**Reference**: [Code - Checklist - FastAPI.md](c:\coding\gridflow-microservices-codex-taskmaster\docs\initial\best-practices\FastAPI DEV detailed\EXAMPLES (DETAILED)\EXAMPLES (DETAILED)\code-quality\Code - Checklist - FastAPI.md) lines 123-129

**Violations**:
- `kafka_consumer_base.py` lines 37-47: calls `claim()` then `handle_event()` with no commit/rollback
- `processed_message_store.py` line 44: starts transaction only if `not in_transaction()` (implicit assumption)
- Correctness depends on caller committing after success (not enforced)

### 8. Testing structure incomplete

**Standard**: Separate unit/integration/property-based/battle/chaos tests
**Reference**: User rules mention battle and chaos tests for appropriate cases

**Current state**:
- Has: unit, integration, property_based
- Missing: battle tests, chaos tests (may not be needed for this service)

## Architecture adherence

### Acceptable differences

The eventing service is **cross-cutting infrastructure**, not a bounded context app:
- Empty `domain/` and `application/` layers (logic in `core.contracts`)
- No `apps/` folder (not applicable)
- No `shared/` folder (uses PyPI toolkit packages instead)

### Technology stack differences

**Standard**: RabbitMQ + FastStream
**Actual**: Kafka + FastStream

This is acceptable (FastStream supports both), but differs from `06_EVENT_PATTERNS.md` examples.

## Verification checklist

### Code quality tools configured (✅ passing)

- [x] Ruff configured with strict rules
- [x] MyPy strict mode enabled
- [x] Pylint for deep checks (max-module-lines=100)
- [x] Bandit for security
- [x] Property-based testing with Hypothesis
- [x] Testcontainers for integration tests
- [x] Coverage ≥80% enforced

### Missing implementations

- [ ] Library logging (standard logging.getLogger + NullHandler) added to all modules
- [ ] Remove `python-structlog-config` dependency (for applications, not libraries)
- [ ] Transactional outbox repository accepts external session
- [ ] FastAPI dependencies created for common resources
- [ ] Files split to ≤100 lines:
  - [ ] Split `event_bus.py` into HandlerResolver, DispatchExecutor, EventBus coordinator
  - [ ] Split test files (210, 175, 167 lines)
  - [ ] Split `outbox_repository.py` (119 lines)
- [ ] DIP violation fixed:
  - [ ] Universal DLQ handler (IEventPublisher interface)
  - [ ] Kafka-specific DLQ handler (separate implementation)
- [ ] Specific exception types vs broad Exception
- [ ] Consumer transaction boundaries clarified

## Detailed findings by category

### Async patterns (mostly ✅)

- ✅ Proper use of async/await for I/O operations
- ✅ AsyncSession throughout
- ✅ No blocking operations detected
- ⚠️  Cannot verify FastStream internals are truly non-blocking

### Type coverage (✅ strong)

- ✅ MyPy strict mode passing
- ✅ Public functions fully typed
- ⚠️  Weak spots: `event_bus.py` line 45 (hasattr check loosens type safety)

### Pydantic validation (✅ good)

- ✅ Settings use pydantic-settings
- ✅ BaseEvent uses Field, validators
- ✅ Registry uses model_validate
- ⚠️  Kafka payloads are dict[str, Any] until deserialization

### Security (✅ configured)

- ✅ Bandit configured
- ✅ Safety for dependency scanning
- ✅ Ruff security rules enabled
- ✅ No hardcoded secrets detected

### Documentation (✅ strong)

- ✅ Google-style docstrings
- ✅ Sphinx + autodoc configured
- ✅ Integration guide present
- ✅ Type hints serve as documentation

## Recommended action priority

**High priority** (breaks patterns or best practices):
1. Add library logging (logging.getLogger + NullHandler pattern) throughout
2. Remove `python-structlog-config` dependency (applications configure logging, not libraries)
3. Fix transactional outbox to accept shared session
4. Split oversized files (especially 210-line test file)
   - Priority: Split `event_bus.py` (101 lines) into HandlerResolver, DispatchExecutor, thin EventBus
   - This also fixes SRP violation

**Medium priority** (improves maintainability):
5. Add FastAPI dependencies for resources
6. Fix DIP violation in DeadLetterHandler:
   - Create universal DLQ handler accepting `IEventPublisher` interface
   - Create separate Kafka-specific DLQ handler for Kafka features
   - Keep implementations explicitly separate (different files/classes)
7. Narrow exception handling

**Low priority** (polish):
8. Add explicit transaction boundaries in consumer

## Positive findings

- Strong type safety with MyPy strict mode
- Excellent test coverage with multiple strategies (unit, integration, property-based)
- Modern tooling (Ruff, Testcontainers, Hypothesis)
- Comprehensive linting configuration
- Transactional outbox pattern **conceptually** implemented (just needs API fix)
- Clean separation of concerns in folder structure
- Good use of interfaces from toolkit packages
- Proper async throughout

## Note on best practices documentation

The `COMMON BEST PRACTICES.md` document (lines 99-108) recommends structured logging (structlog) with the statement "never print()". This guidance is correct for **applications** but needs nuance for **libraries**:

- **Applications** (FastAPI services, CLI tools): Should use structlog/loguru, configure handlers/formatters, set log levels
- **Libraries** (this eventing package): Should use standard `logging.getLogger(__name__)`, add only NullHandler, never configure logging

The Python community consensus (2026) is that libraries should emit logs but delegate all configuration to the consuming application. This prevents conflicts when multiple libraries try to configure logging differently.