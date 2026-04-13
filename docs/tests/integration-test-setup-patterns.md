# Integration test setup patterns for FastStream bridge

**[Setup](#setup)** • **[Containers](#containers)** • **[Isolation](#isolation)** • **[Patterns](#patterns)**

## Critical rule

Every integration test MUST use unique infrastructure identifiers to prevent cross-contamination.

## Setup helpers architecture

### Location

`tests/integration/test_bridge_handler_integration/setup_helpers.py`

### Required functions

```python
def setup_test_containers_config(
    kafka_container: KafkaContainer,
    rabbitmq_container: RabbitMqContainer,
    monkeypatch: pytest.MonkeyPatch,
    exchange: str = "test-events",
    consumer_group_id: str = "eventing-consumers",
) -> tuple[str, str, str]:
    """Configure test containers with unique identifiers.
    
    Returns:
        (kafka_bootstrap_url, rabbitmq_url, consumer_group_id)
    """
    kafka_bootstrap = kafka_container.get_bootstrap_server()
    rabbitmq_url = f"amqp://{rabbitmq_container.username}:..."
    
    monkeypatch.setattr(app_settings, "kafka_bootstrap_servers", kafka_bootstrap)
    monkeypatch.setattr(app_settings, "rabbitmq_url", rabbitmq_url)
    monkeypatch.setattr(app_settings, "rabbitmq_exchange", exchange)
    
    return kafka_bootstrap, rabbitmq_url, consumer_group_id


def initialize_production_bridge(
    session_factory: Any,
    consumer_group_id: str = "eventing-consumers",
) -> tuple[KafkaBroker, RabbitBroker]:
    """Initialize production bridge with configurable consumer group."""
    broker, rabbit_broker, rabbit_publisher = initialize_brokers_and_publishers()
    bridge_config = initialize_bridge_config(consumer_group_id=consumer_group_id)
    register_bridge_handler(broker, bridge_config, rabbit_publisher, session_factory)
    return broker, rabbit_broker
```

## Container fixtures

### Required pytest fixtures

From `tests/conftest_modules/container_fixtures.py`:

```python
@pytest.fixture(scope="session")
def kafka_container() -> KafkaContainer:
    """Kafka container for integration tests."""
    with KafkaContainer() as kafka:
        kafka.start()
        yield kafka

@pytest.fixture(scope="session")
def rabbitmq_container() -> RabbitMqContainer:
    """RabbitMQ container for integration tests."""
    with RabbitMqContainer() as rabbit:
        rabbit.start()
        yield rabbit
```

### Database fixtures

From `tests/conftest_modules/database_fixtures.py`:

```python
@pytest.fixture
def sqlite_session_factory() -> tuple[Engine, async_sessionmaker]:
    """In-memory SQLite for fast unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session_factory = async_sessionmaker(engine, ...)
    return engine, async_session_factory
```

## Isolation checklist per test

```python
@pytest.mark.integration
@pytest.mark.requires_kafka
@pytest.mark.requires_rabbitmq
class TestMyFeature:
    @pytest.mark.asyncio
    async def test_my_scenario(
        self,
        kafka_container,      # Session-scoped container
        rabbitmq_container,   # Session-scoped container
        sqlite_session_factory,  # Function-scoped DB
        monkeypatch,          # For settings override
    ) -> None:
        # 1. UNIQUE infrastructure IDs
        kafka_bootstrap, rabbitmq_url, group_id = setup_test_containers_config(
            kafka_container,
            rabbitmq_container,
            monkeypatch,
            exchange=f"test-events-my-feature-{uuid4()}",  # UNIQUE
            consumer_group_id=f"my-feature-test-{uuid4()}",  # UNIQUE
        )
        
        # 2. Initialize bridge with unique group
        _, async_session_factory = sqlite_session_factory
        broker, rabbit_broker = initialize_production_bridge(
            async_session_factory,
            consumer_group_id=group_id
        )
        
        # 3. Use async context managers
        async with broker, rabbit_broker:
            await broker.start()
            await rabbit_broker.start()
            
            # 4. Create unique RabbitMQ resources
            connection = await aio_pika.connect_robust(rabbitmq_url)
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                f"test-events-my-feature-{uuid4()}",  # Matches setup
                ExchangeType.TOPIC,
                durable=True
            )
            queue = await channel.declare_queue(
                f"test-queue-{uuid4()}",  # ALWAYS unique
                auto_delete=True
            )
            await queue.bind(exchange, routing_key="#")
            
            # 5. Wait for infrastructure readiness
            await asyncio.sleep(5)
            
            # ... test implementation ...
            
            await connection.close()
```

## Timing considerations

Integration tests require adequate sleep/wait times:

```python
# After container setup
await asyncio.sleep(5)  # Allow brokers to fully start

# After publishing to Kafka
producer.produce("events", value=json_data)
producer.flush()
await asyncio.sleep(8)  # Allow FastStream to process + publish to RabbitMQ

# Before assertions
try:
    msg = await asyncio.wait_for(queue.get(timeout=5), timeout=6)
except TimeoutError:
    pytest.fail("Message not received within timeout")
```

**Rule**: Use sleep times from working tests as baseline. If tests flaky, increase incrementally.

## Test structure

```
tests/integration/test_bridge_handler_integration/
├── __init__.py
├── setup_helpers.py              # Shared setup, UNIQUE IDs per test
├── test_message_forwarding.py   # Tests Kafka → RabbitMQ flow
├── test_idempotency.py           # Tests duplicate prevention
├── test_exception_nack.py        # Tests error handling + nack
└── test_empty_json.py            # Tests edge cases
```

Each test file:
- Imports from `setup_helpers`
- Passes unique identifiers
- < 100 lines (split to sub-folder if needed)
- Isolated from other tests

## Required test markers

```python
@pytest.mark.integration       # Requires infrastructure
@pytest.mark.requires_kafka    # Needs Kafka container
@pytest.mark.requires_rabbitmq # Needs RabbitMQ container
```

Configuration in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration (requires infrastructure)",
    "requires_kafka: marks tests requiring Kafka",
    "requires_rabbitmq: marks tests requiring RabbitMQ",
]
```

## Pattern summary

**DO**:
- Generate unique IDs using uuid4() for exchanges, queues, consumer groups
- Pass consumer_group_id through entire setup chain
- Use function-scoped sqlite for database isolation
- Wait adequate time for async operations
- Clean up connections explicitly

**DON'T**:
- Share consumer group IDs between tests
- Assume Kafka topic is clean
- Rely on message ordering across tests
- Hardcode infrastructure identifiers
- Skip waiting for infrastructure readiness
