# Coverage Strategy

**[Quick](#quick)** • **[Thresholds](#thresholds)** • **[Rationale](#rationale)** • **[Validation](#validation)**

## Quick

**Overall: 80% | Critical Paths: 85%**

- **Overall project**: 80% coverage (pytest `--cov-fail-under=80`)
- **Critical infrastructure**: 85% coverage minimum (enforced by `scripts/check_coverage_thresholds.py`)
- **Risk-based approach**: Tiered thresholds, not blanket percentages
- **Ratcheting**: Pre-commit hooks prevent coverage drops

## Thresholds

### Critical Infrastructure (85% minimum)

**Core business logic & resilience:**
- `src/messaging/core/contracts/circuit_breaker.py`
- `src/messaging/core/contracts/bus/`
- `src/messaging/core/contracts/dispatcher_setup.py`

**Message processing & idempotency:**
- `src/messaging/main/_initialization.py` (bridge handler with manual ack fixes)
- `src/messaging/infrastructure/persistence/processed_message_store/`
- `src/messaging/infrastructure/outbox/outbox_repository.py`
- `src/messaging/infrastructure/outbox/outbox_crud/`

**Pub/sub bridge & publishers:**
- `src/messaging/infrastructure/pubsub/bridge/`
- `src/messaging/infrastructure/pubsub/kafka_publisher.py`
- `src/messaging/infrastructure/pubsub/rabbit/publisher.py`

**Resilience middleware:**
- `src/messaging/infrastructure/resilience/` (circuit breaker, rate limiter)

### Standard Infrastructure (80% target)

All other production code maintains the 80% overall threshold.

## Rationale

Per 2026 best practices (Fowler, Google Testing Blog, Microsoft DevOps):

**Why tiered thresholds?**
1. **Risk-based**: Business-critical paths require higher confidence
2. **Pragmatic**: Configuration/boilerplate can have lower coverage
3. **Focus**: Forces effort on high-value, high-risk code
4. **Realistic**: Acknowledges some code is harder to test (UI, infra setup)

**Why 85% for critical paths?**
- Kafka/RabbitMQ message processing → data loss risk
- Idempotency store → duplicate event risk
- Circuit breaker → cascading failure risk
- Transactional outbox → ordering guarantee risk

**Why 80% overall?**
- Industry standard for backend services (2020-2026)
- Balances confidence with diminishing returns
- Excludes trivial code (`__repr__`, `NotImplementedError`, type stubs)

## Validation

### Local Development

Run tests with coverage:
```bash
poetry run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```

Check tiered thresholds:
```bash
poetry run python scripts/check_coverage_thresholds.py
```

View HTML report:
```bash
# Windows
start htmlcov/index.html

# Unix/Linux
xdg-open htmlcov/index.html
```

### CI/CD (GitHub Actions)

1. **Overall threshold**: Enforced by pytest `--cov-fail-under=80`
2. **Critical path thresholds**: Enforced by `scripts/check_coverage_thresholds.py`
3. **Ratcheting**: PRs must not decrease overall coverage

Workflow: `.github/workflows/tests.yml`

### Pre-commit Hooks

Future: Add pre-commit hook to prevent coverage drops:
```yaml
# .pre-commit-config.yaml (future)
- repo: local
  hooks:
    - id: check-coverage
      name: Check coverage thresholds
      entry: poetry run python scripts/check_coverage_thresholds.py
      language: system
      pass_filenames: false
```

## Codebase Analysis

Critical paths identified via Serena MCP analysis (2026-04-09):

**Search patterns used:**
- `class.*(Store|Repository|Consumer|Publisher|Broker|Handler)`
- `class CircuitBreaker|class RateLimiter|class.*Middleware`

**Key architectural components identified:**
1. **Message processing**: `_initialization.py` orchestrates broker setup, subscriber registration, and message handling
2. **Idempotency**: `SqlAlchemyProcessedMessageStore` prevents duplicate event processing
3. **Resilience**: Circuit breaker and rate limiter protect downstream services
4. **Pub/sub bridge**: Kafka-to-RabbitMQ bridge enables cross-broker event forwarding

## References

- [Google Testing Blog: Code Coverage Best Practices](https://testing.googleblog.com/2020/08/code-coverage-best-practices.html)
- [Martin Fowler: TestCoverage](https://martinfowler.com/bliki/TestCoverage.html)
- [Microsoft DevOps: Test Coverage](https://learn.microsoft.com/en-us/azure/devops/pipelines/test/codecoverage)
- Context7 MCP: FastStream documentation (manual ack, transactional patterns)
- Serena MCP: Codebase analysis for critical path identification
