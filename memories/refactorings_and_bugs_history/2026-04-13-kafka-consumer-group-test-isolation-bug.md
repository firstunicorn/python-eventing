# Kafka consumer group test isolation bug

**[Bug](#bug)** • **[Root cause](#root-cause)** • **[Fix](#fix)** • **[Prevention](#prevention)**

## Bug

Integration test `test_idempotency` failed consistently in CI:

```python
AssertionError: assert 2 == 1
  where 2 = len([
    {'event_id': 'exception-test-{uuid}', 'event_type': 'order.created', ...},
    {'event_id': 'idempotent-prod-{uuid}', 'event_type': 'order.placed', ...}
  ])
```

Test expected 1 message but received 2. Second message came from different test.

## Root cause

**Shared Kafka consumer group causes message cross-contamination**.

### Architecture before fix

```
Test A (test_exception_nack)
  └─> Publishes to topic "events"
         │
         ├─> Consumer group "eventing-consumers" (shared)
         │   └─> Receives message A
         │
Test B (test_idempotency)
  └─> Publishes to topic "events"
         │
         └─> Consumer group "eventing-consumers" (SAME)
             └─> Receives message A + message B (contaminated!)
```

### How Kafka consumer groups work

1. **Consumer group maintains offset state** per topic partition
2. All consumers in same group share offset tracking
3. When test B starts, it joins group that already processed test A's messages
4. But if test A's messages haven't been fully consumed, test B receives them
5. Even with separate RabbitMQ exchanges, **Kafka topic is shared**

### Hardcoded consumer group ID

**Location**: `src/messaging/main/_initialization/bridge_setup/handler_registration.py:33`

```python
@broker.subscriber(
    bridge_config.kafka_topic,
    ack_policy=AckPolicy.MANUAL,
    group_id="eventing-consumers",  # HARDCODED - shared across all tests
)
```

### Why RabbitMQ exchange isolation wasn't enough

Initially attempted fix:
- `test_exception_nack` → exchange: "test-events-exception-nack"
- `test_idempotency` → exchange: "test-events-idempotency"

**This didn't work because**:
- Kafka consumer reads from **topic**, not exchange
- Both tests use same Kafka topic "events"  
- Both tests use same consumer group "eventing-consumers"
- RabbitMQ isolation only affects where messages are published AFTER Kafka consumption

## Fix

### Phase 1: Make consumer group configurable

**1. Add field to BridgeConfig** (`src/messaging/infrastructure/pubsub/bridge/config.py`):
```python
@dataclass(frozen=True, slots=True)
class BridgeConfig:
    kafka_topic: str
    rabbitmq_exchange: str
    routing_key_template: str
    consumer_group_id: str  # NEW FIELD
```

**2. Update config initialization** (`src/messaging/main/_initialization/bridge_setup/config.py`):
```python
def initialize_bridge_config(consumer_group_id: str = "eventing-consumers") -> BridgeConfig:
    return BridgeConfig(
        kafka_topic="events",
        rabbitmq_exchange=settings.rabbitmq_exchange,
        routing_key_template="{event_type}",
        consumer_group_id=consumer_group_id,  # Use parameter
    )
```

**3. Use dynamic group ID** (`src/messaging/main/_initialization/bridge_setup/handler_registration.py`):
```python
@broker.subscriber(
    bridge_config.kafka_topic,
    ack_policy=AckPolicy.MANUAL,
    group_id=bridge_config.consumer_group_id,  # Dynamic from config
)
```

### Phase 2: Update test infrastructure

**4. Update setup helper** (`tests/integration/test_bridge_handler_integration/setup_helpers.py`):
```python
def setup_test_containers_config(
    kafka_container,
    rabbitmq_container,
    monkeypatch,
    exchange: str = "test-events",
    consumer_group_id: str = "eventing-consumers",  # NEW PARAMETER
) -> tuple[str, str, str]:  # Returns (kafka_url, rabbit_url, group_id)
    # ... setup code ...
    return kafka_bootstrap, rabbitmq_url, consumer_group_id

def initialize_production_bridge(
    session_factory,
    consumer_group_id: str = "eventing-consumers",  # NEW PARAMETER
) -> tuple[Any, Any]:
    broker, rabbit_broker, rabbit_publisher = initialize_brokers_and_publishers()
    bridge_config = initialize_bridge_config(consumer_group_id=consumer_group_id)  # Pass through
    register_bridge_handler(broker, bridge_config, rabbit_publisher, session_factory)
    return broker, rabbit_broker
```

### Phase 3: Isolate each test

**5. test_idempotency.py**:
```python
async def test_production_handler_idempotency(self, ...):
    kafka_bootstrap, rabbitmq_url, group_id = setup_test_containers_config(
        kafka_container, rabbitmq_container, monkeypatch,
        exchange="test-events-idempotency",
        consumer_group_id="idempotency-test-group",  # UNIQUE
    )
    broker, rabbit_broker = initialize_production_bridge(
        async_session_factory,
        consumer_group_id=group_id  # Pass unique ID
    )
```

**6. test_exception_nack.py**:
```python
async def test_bridge_handler_exception_path_triggers_nack(self, ...):
    kafka_bootstrap, rabbitmq_url, group_id = setup_test_containers_config(
        kafka_container, rabbitmq_container, monkeypatch,
        exchange="test-events-exception-nack",
        consumer_group_id="exception-nack-test-group",  # UNIQUE
    )
    broker, rabbit_broker = initialize_production_bridge(
        async_session_factory,
        consumer_group_id=group_id  # Pass unique ID
    )
```

## Architecture after fix

```
Test A (test_exception_nack)
  └─> Consumer group "exception-nack-test-group" (isolated)
      └─> Receives ONLY test A messages

Test B (test_idempotency)  
  └─> Consumer group "idempotency-test-group" (isolated)
      └─> Receives ONLY test B messages
```

## Prevention

**Rule**: Every integration test using Kafka MUST have unique consumer group ID.

**Pattern**:
```python
@pytest.mark.integration
@pytest.mark.requires_kafka
class TestMyFeature:
    async def test_something(self, kafka_container, ...):
        # ALWAYS pass unique consumer_group_id
        _, _, group_id = setup_test_containers_config(
            kafka_container, rabbitmq_container, monkeypatch,
            consumer_group_id=f"my-feature-test-{uuid4()}"  # Unique per test run
        )
        
        broker, _ = initialize_production_bridge(
            session_factory,
            consumer_group_id=group_id
        )
```

**Checklist for new Kafka integration tests**:
- [ ] Unique consumer_group_id passed to setup
- [ ] Unique exchange name (RabbitMQ isolation)
- [ ] Unique queue names using uuid4()
- [ ] Test doesn't assume clean Kafka state
- [ ] Test doesn't rely on message ordering from other tests

## Lessons learned

1. **Infrastructure isolation requires multiple layers**: RabbitMQ exchange isolation alone insufficient
2. **Kafka consumer groups persist state**: Shared group ID = shared offset = cross-contamination
3. **Hardcoded infrastructure IDs are anti-pattern**: Always make configurable for testing
4. **Test failures cryptic**: "Expected 1 got 2" doesn't reveal cross-contamination source
5. **CI failures more reliable**: Local tests might pass due to timing, CI consistently fails

## Related issues

- 1 integration test failed initially
- RabbitMQ exchange isolation attempted first (insufficient)
- Required making consumer_group_id configurable throughout stack
- 6 files modified total to achieve proper isolation
