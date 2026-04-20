# Test isolation architecture

**[Root cause](#root-cause)** • **[Solution](#solution)** • **[Integration tests](#integration-tests)** • **[Unit tests](#unit-tests)**

## Critical rule

Integration tests using shared infrastructure (Kafka, RabbitMQ) MUST use unique identifiers for:
- **Kafka topic names** (most critical - topics store messages)
- Consumer group IDs (Kafka - tracks offsets)
- Exchange names (RabbitMQ)  
- Queue names (RabbitMQ)

**Both Kafka topic AND consumer group must be unique per test**.

Failure to isolate causes message cross-contamination between tests.

## Root cause

Kafka consumer groups maintain offset state across topic partitions. When multiple tests share the same consumer group ID:

1. Test A publishes message to topic "events"
2. Test B also uses topic "events" with SAME consumer group
3. Test B's consumer receives BOTH its own messages AND Test A's messages
4. Assertions fail: `assert len(messages) == 1` but gets 2+

**Real example from our codebase**:
```python
# test_exception_nack.py publishes:
{"event_id": "exception-test-{uuid}", "event_type": "order.created"}

# test_idempotency.py expects only:
{"event_id": "idempotent-prod-{uuid}", "event_type": "order.placed"}

# But receives BOTH because same consumer group "messagekit-consumers"
```

## Solution

### Integration tests pattern

```python
# tests/integration/test_bridge_handler_integration/setup_helpers.py
def setup_test_containers_config(
    kafka_container,
    rabbitmq_container,
    monkeypatch,
    kafka_topic: str = "events",
    exchange: str = "test-events",
    consumer_group_id: str = "messagekit-consumers",
) -> tuple[str, str, str]:  # Returns (kafka_url, rabbit_url, group_id)
    """Configure app settings with UNIQUE test identifiers."""
    # Monkeypatch settings with unique values
    monkeypatch.setattr(app_settings, "rabbitmq_exchange", exchange)
    # Return group_id for use in bridge initialization
    return kafka_bootstrap, rabbitmq_url, consumer_group_id
```

**Per-test usage**:
```python
@pytest.mark.integration
class TestIdempotency:
    async def test_production_handler_idempotency(self, ...):
        # Unique topic, exchange, AND consumer group
        kafka_bootstrap, rabbitmq_url, group_id = setup_test_containers_config(
            kafka_container, 
            rabbitmq_container, 
            monkeypatch,
            kafka_topic="events-idempotency-test",  # UNIQUE TOPIC
            exchange="test-events-idempotency",  # Unique exchange
            consumer_group_id="idempotency-test-group"  # Unique consumer group
        )
        
        # Initialize bridge with unique topic and group_id
        broker, rabbit_broker = initialize_production_bridge(
            async_session_factory,
            consumer_group_id=group_id,
            kafka_topic="events-idempotency-test",  # Pass through
        )
```

### Unit tests pattern

**Mock parameter ordering rule**:

Python applies decorators bottom-to-top, parameters received top-to-bottom:

```python
# CORRECT
@patch("module.function_b")  # Applied 2nd, received as param 2
@patch("module.function_a")  # Applied 1st, received as param 1  
def test_example(self, mock_a, mock_b):  # Order: a, b
    pass

# WRONG (causes test failures)
@patch("module.function_b")  # Applied 2nd
@patch("module.function_a")  # Applied 1st
def test_example(self, mock_b, mock_a):  # REVERSED - fails
    pass
```

## Integration tests architecture

### File structure

```
tests/integration/test_bridge_handler_integration/
├── __init__.py
├── setup_helpers.py           # Shared setup with configurable IDs
├── test_message_forwarding.py # Uses group "forwarding-test"
├── test_idempotency.py        # Uses group "idempotency-test"
├── test_exception_nack.py     # Uses group "exception-nack-test"
└── test_empty_json.py         # Uses group "empty-json-test"
```

### Setup helpers contract

```python
def setup_test_containers_config(
    kafka_container,
    rabbitmq_container, 
    monkeypatch,
    kafka_topic: str = "events",
    exchange: str = "test-events",
    consumer_group_id: str = "messagekit-consumers",
) -> tuple[str, str, str]:
    """Configure test containers with unique identifiers.
    
    Returns:
        Tuple of (kafka_bootstrap_url, rabbitmq_url, consumer_group_id)
    """
    pass

def initialize_production_bridge(
    session_factory,
    consumer_group_id: str = "messagekit-consumers",
    kafka_topic: str = "events",
) -> tuple[KafkaBroker, RabbitBroker]:
    """Initialize bridge with configurable topic and consumer group."""
    pass
```

## Unit tests architecture

### Mock verification patterns

Always verify mocks were called correctly:

```python
def test_passes_settings_to_kafka_broker(
    self, mock_create_kafka, mock_create_rabbit  # Correct order
) -> None:
    initialize_brokers_and_publishers()
    
    # Verify called once
    mock_create_kafka.assert_called_once()
    
    # Verify positional args
    call_args = mock_create_kafka.call_args
    assert call_args[0][0] is settings
    
    # Verify keyword args
    kwargs = mock_create_kafka.call_args.kwargs
    assert "enable_rate_limiter" in kwargs
```

### Files under 100 lines

Split test files exceeding 100-line limit into sub-folders:

```
tests/integration/test_bridge_handler_integration/
├── test_idempotency/
│   ├── __init__.py
│   ├── test_duplicate_prevention.py  # < 100 lines
│   └── test_offset_management.py     # < 100 lines
└── test_exception_nack/
    ├── __init__.py
    └── test_nack_behavior.py          # < 100 lines
```

## Critical checklist

Before creating integration tests:
- [ ] Unique kafka_topic per test (most critical)
- [ ] Unique consumer_group_id per test
- [ ] Unique exchange name per test  
- [ ] Unique queue names (use uuid4())
- [ ] Mock parameter order matches decorator order
- [ ] Setup helpers return all config values needed
- [ ] Each test file < 100 lines
