---
name: "File splitting plan: enforce 100-line limit"
overview: Split 13 Python files exceeding 100-line limit into modular sub-folders. Each file will become a folder with the same name (minus extension), containing split modules that preserve all code, comments, and formatting without degradation.
todos: []
isProject: false
---

# File splitting plan: enforce 100-line limit

## Detected violations (via pylint C0302)

Total: 13 files exceeding 100 lines

### Source code files (3)

1. [`src/messaging/main/_initialization.py`](src/messaging/main/_initialization.py) - **189 lines**
   - Split into `_initialization/` folder:
     - `broker_setup.py` - Broker and publisher initialization functions
     - `bridge_setup.py` - Bridge configuration and handler registration
     - `health_check_setup.py` - Health check initialization
     - `__init__.py` - Re-export all functions

2. [`src/messaging/infrastructure/outbox/outbox_crud/operations.py`](src/messaging/infrastructure/outbox/outbox_crud/operations.py) - **105 lines**
   - Split into `operations/` folder:
     - `writers.py` - Create/update/delete operations
     - `readers.py` - Query operations
     - `__init__.py` - Re-export all classes

3. [`src/messaging/infrastructure/pubsub/broker_config/factory.py`](src/messaging/infrastructure/pubsub/broker_config/factory.py) - **104 lines**
   - Split into `factory/` folder:
     - `kafka_factory.py` - Kafka broker creation
     - `rabbit_factory.py` - RabbitMQ broker creation
     - `__init__.py` - Re-export factory functions

### Test files (10)

4. [`tests/conftest.py`](tests/conftest.py) - **452 lines** (CRITICAL - largest file)
   - Split into `conftest/` folder:
     - `hypothesis_config.py` - Hypothesis profile setup
     - `database_fixtures.py` - SQLite/Postgres fixtures
     - `kafka_fixtures.py` - Kafka container and client fixtures
     - `rabbitmq_fixtures.py` - RabbitMQ container fixtures
     - `application_fixtures.py` - FastAPI app and HTTP client fixtures
     - `session_hooks.py` - pytest_sessionstart/end cleanup hooks
     - `__init__.py` - Import and register all fixtures

5. [`tests/integration/test_faststream_library_verification.py`](tests/integration/test_faststream_library_verification.py) - **509 lines** (largest test)
   - Split into `test_faststream_library_verification/` folder:
     - `test_manual_ack.py` - Manual acknowledgment test class
     - `test_json_errors.py` - JSON validation error test class
     - `test_consume_scope.py` - Consume scope middleware test class
     - `test_publish_scope.py` - Publish scope middleware test class
     - `test_after_processed.py` - After processed hook test class
     - `__init__.py` - Empty (test discovery)

6. [`tests/integration/test_bridge_handler_integration.py`](tests/integration/test_bridge_handler_integration.py) - **321 lines**
   - Split into `test_bridge_handler_integration/` folder:
     - `test_production_handler.py` - Production bridge handler tests
     - `test_exception_paths.py` - Exception handling tests
     - `__init__.py` - Empty (test discovery)

7. [`tests/chaos/test_circuit_breaker_resilience.py`](tests/chaos/test_circuit_breaker_resilience.py) - **195 lines**
   - Split into `test_circuit_breaker_resilience/` folder:
     - `test_kafka_failures.py` - Kafka circuit breaker tests
     - `test_rabbitmq_failures.py` - RabbitMQ circuit breaker tests
     - `__init__.py` - Empty

8. [`tests/integration/test_consumer_group_config.py`](tests/integration/test_consumer_group_config.py) - **159 lines**
   - Split into `test_consumer_group_config/` folder:
     - `test_group_assignment.py` - Consumer group tests
     - `test_partition_strategy.py` - Partition assignment tests
     - `__init__.py` - Empty

9. [`tests/integration/test_kafka_rabbitmq_bridge.py`](tests/integration/test_kafka_rabbitmq_bridge.py) - **155 lines**
   - Split into `test_kafka_rabbitmq_bridge/` folder:
     - `test_bridge_routing.py` - Routing and publishing tests
     - `test_idempotency.py` - Idempotency tests
     - `test_error_handling.py` - Malformed message tests
     - `__init__.py` - Empty

10. [`tests/chaos/test_kafka_connection_resilience/test_reconnection.py`](tests/chaos/test_kafka_connection_resilience/test_reconnection.py) - **140 lines**
    - Split into `test_reconnection/` folder:
      - `test_producer_restart.py` - Producer reconnection tests
      - `test_consumer_restart.py` - Consumer reconnection tests
      - `__init__.py` - Empty

11. [`tests/integration/test_dlq_admin_api.py`](tests/integration/test_dlq_admin_api.py) - **125 lines**
    - Split into `test_dlq_admin_api/` folder:
      - `test_list_messages.py` - DLQ listing tests
      - `test_requeue.py` - Message requeue tests
      - `__init__.py` - Empty

12. [`tests/integration/test_kafka_consumer_groups/test_same_group_distribution.py`](tests/integration/test_kafka_consumer_groups/test_same_group_distribution.py) - **125 lines**
    - Split into `test_same_group_distribution/` folder:
      - `test_single_consumer.py` - Single consumer tests
      - `test_multi_consumer.py` - Multiple consumer tests
      - `__init__.py` - Empty

13. [`tests/integration/test_testcontainers_smoke/test_kafka_postgres.py`](tests/integration/test_testcontainers_smoke/test_kafka_postgres.py) - **124 lines**
    - Split into `test_kafka_postgres/` folder:
      - `test_kafka_smoke.py` - Kafka smoke tests
      - `test_postgres_smoke.py` - Postgres smoke tests
      - `__init__.py` - Empty

## Serena MCP usage (CRITICAL)

**MANDATORY**: Use Serena MCP for all code manipulation operations on existing files.

### Serena MCP workflow for each file split

1. **Activate project**: Use `activate_project` tool before any operations
2. **Analyze structure**: Use `get_symbols_overview` on file to identify all classes/functions
3. **Verify references**: Use `find_referencing_symbols` for each symbol to find all import locations
4. **Extract code**: Use Serena's symbol extraction to copy code structures to new files
5. **Move operations**: Use `replace_symbol_body` and `insert_after_symbol` for relocating code
6. **Verify no orphans**: After moving, use `find_referencing_symbols` to confirm no references to old locations remain

### Why Serena MCP

- Ensures precise symbol-level operations without manual copy-paste errors
- Tracks all references automatically (catches imports we might miss manually)
- Safer than text-based tools for refactoring existing code
- Required by project standards for manipulating existing codebase

## Splitting rules (per user requirements)

1. **No trimming**: Preserve all code, comments, docstrings, formatting
2. **No compression**: Don't degrade styling/formatting to fit lines
3. **Complete transfer**: Every line moves to new location - zero data loss
4. **Sub-folder structure**: Create folder named after original file (minus `.py`)
5. **No extraction comments**: Don't add "extracted from X" comments
6. **No backward compatibility**: Assume zero users, no migration path needed
7. **Import updates**: Update all imports in other files to point to new structure
8. **Preserve test discovery**: Ensure pytest can still find all tests
9. **Use Serena MCP**: MANDATORY for all code manipulation operations

## Implementation steps

1. **Activate Serena MCP**
   - Use `activate_project` tool with project root path
   - Verify Serena MCP is working before proceeding

2. **Run pylint to confirm violations**
   ```bash
   poetry run pylint src/ tests/ --max-module-lines=100 --disable=all --enable=too-many-lines
   ```

3. **Split each file** (3 source + 10 test files)
   - For each file:
     - Use `get_symbols_overview` to analyze structure
     - Use `find_referencing_symbols` for each symbol to map dependencies
     - Create subfolder with original filename (minus `.py`)
     - Use Serena MCP tools to extract and move code to new modules
     - Create `__init__.py` with re-exports
     - Update imports in dependent files (found via `find_referencing_symbols`)
     - Use `find_referencing_symbols` again to verify no orphaned references
   - Verify no functionality lost

4. **Delete original files** after confirming splits are complete

5. **Run linters to verify compliance**
   ```bash
   poetry run ruff check src/ tests/
   poetry run mypy src/
   poetry run pylint src/ tests/ --max-module-lines=100 --disable=all --enable=too-many-lines
   ```

6. **Verify no new violations** - confirm all files now under 100 lines

## Expected outcome

- All 13 files split into modular folders
- Zero files exceeding 100 lines (pylint C0302 clean)
- All code, comments, formatting preserved exactly
- Linters pass (ruff, mypy, pylint)
- Test discovery works (pytest can find all tests)
- Ready for commit (tests and commit will be done later by user)
