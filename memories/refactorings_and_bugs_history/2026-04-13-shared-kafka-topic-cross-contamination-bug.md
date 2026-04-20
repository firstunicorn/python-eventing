# Shared Kafka topic cross-contamination bug

**[Problem](#problem)** • **[Root cause](#root-cause)** • **[Fix](#fix)** • **[Lessons](#lessons)**

## Problem

Test `test_idempotency` received messages from `test_exception_nack` even though they used DIFFERENT consumer groups.

```
AssertionError: assert 2 == 1
  where 2 = len([
    {'event_id': 'exception-test-57190041-d5f0-4cf5-945e-e363868fbcd6', 
     'event_type': 'order.created', 
     'payload': {'order_id': 999}, 
     'timestamp': '2026-01-01T00:00:00Z'},  # From test_exception_nack
    {'event_id': 'idempotent-prod-13285245-944e-42e1-899d-520ed64b366a', 
     'event_type': 'order.placed', 
     'data': {'order_id': 456}}   # Own message
  ])
```

**Expected**: 1 message
**Received**: 2 messages (one from different test)

## Root cause

**Unique consumer groups weren't enough - shared Kafka topic was the issue**.

### Why consumer group isolation failed

1. `test_exception_nack`: consumer_group="exception-nack-test-group", topic="events"
2. `test_idempotency`: consumer_group="idempotency-test-group", topic="events" (SAME)
3. Both tests bind RabbitMQ queues with overlapping routing keys ("order.#")
4. Messages from both tests visible to both consumers

### Kafka architecture explained

**Consumer groups provide offset isolation, NOT message isolation**:

- **Topic** = actual message store (messages persist here)
- **Consumer group** = offset tracking mechanism (which messages consumed)
- Multiple groups can read same topic independently
- But ALL groups reading same topic see ALL messages

```
Topic "events" contains:
├─ message A (from test_exception_nack)
├─ message B (from test_idempotency)
└─ message C (from test_empty_json)

Consumer group "exception-nack-test-group":
├─ Reads topic "events"
└─ Sees: A, B, C (ALL messages)

Consumer group "idempotency-test-group":
├─ Reads topic "events" (SAME TOPIC)
└─ Sees: A, B, C (ALL messages) ← CONTAMINATED
```

### Why RabbitMQ exchange isolation wasn't enough

Initial attempted fix:
- `test_exception_nack` → exchange: "test-events-exception-nack"
- `test_idempotency` → exchange: "test-events-idempotency"

**This didn't work because**:
- Kafka consumer reads from **topic**, not exchange
- Both tests use same Kafka topic "events"  
- Both tests use same consumer group pattern
- RabbitMQ isolation only affects where messages are published AFTER Kafka consumption
- Cross-contamination happens BEFORE RabbitMQ (at Kafka level)

## Fix

### Phase 1: Make kafka_topic configurable in setup

**Modified setup_helpers.py**:

```python
def setup_test_containers_config(
    kafka_container,
    rabbitmq_container,
    monkeypatch,
    exchange: str = "test-events",
    consumer_group_id: str = "eventing-consumers",
    kafka_topic: str = "events",  # NEW PARAMETER
) -> tuple[str, str, str]:
    """Configure with unique identifiers per test."""
    kafka_bootstrap = kafka_container.get_bootstrap_server()
    rabbitmq_url = f"amqp://..."
    
    monkeypatch.setattr(settings, "kafka_bootstrap_servers", kafka_bootstrap)
    monkeypatch.setattr(settings, "rabbitmq_url", rabbitmq_url)
    monkeypatch.setattr(settings, "rabbitmq_exchange", exchange)
    
    return kafka_bootstrap, rabbitmq_url, consumer_group_id


def initialize_production_bridge(
    session_factory,
    consumer_group_id: str = "eventing-consumers",
    kafka_topic: str = "events",  # NEW PARAMETER
) -> tuple[Any, Any]:
    """Initialize bridge with configurable topic."""
    from messagekit.infrastructure.pubsub.bridge.config import BridgeConfig
    
    broker, rabbit_broker, rabbit_publisher = initialize_brokers_and_publishers()
    bridge_config = BridgeConfig(
        kafka_topic=kafka_topic,  # Dynamic from parameter
        rabbitmq_exchange=app_settings.rabbitmq_exchange,
        routing_key_template="{event_type}",
        consumer_group_id=consumer_group_id,
    )
    register_bridge_handler(broker, bridge_config, rabbit_publisher, session_factory)
    return broker, rabbit_broker
```

### Phase 2: Each test uses unique topic

**Modified test_idempotency.py**:

```python
async def test_production_handler_idempotency(self, ...):
    kafka_bootstrap, rabbitmq_url, consumer_group_id = setup_test_containers_config(
        kafka_container,
        rabbitmq_container,
        monkeypatch,
        exchange="test-events-idempotency",
        consumer_group_id="idempotency-test-group",
        kafka_topic="events-idempotency-test",  # UNIQUE TOPIC
    )
    
    broker, rabbit_broker = initialize_production_bridge(
        async_session_factory,
        consumer_group_id=consumer_group_id,
        kafka_topic="events-idempotency-test",  # Pass through
    )
    
    # Publish to UNIQUE topic
    producer.produce("events-idempotency-test", value=json.dumps(test_msg).encode())
    
    # Second duplicate message
    producer.produce("events-idempotency-test", value=json.dumps(test_msg).encode())
```

**Modified test_exception_nack.py**:

```python
async def test_bridge_handler_exception_path_triggers_nack(self, ...):
    kafka_bootstrap, rabbitmq_url, consumer_group_id = setup_test_containers_config(
        kafka_container,
        rabbitmq_container,
        monkeypatch,
        exchange="test-events-exception-nack",
        consumer_group_id="exception-nack-test-group",
        kafka_topic="events-exception-nack-test",  # UNIQUE TOPIC
    )
    
    broker, rabbit_broker = initialize_production_bridge(
        async_session_factory,
        consumer_group_id=consumer_group_id,
        kafka_topic="events-exception-nack-test",  # Pass through
    )
    
    # Publish to UNIQUE topic
    producer.produce("events-exception-nack-test", value=json.dumps(message).encode())
```

**Modified test_empty_json.py**:

```python
async def test_production_handler_with_empty_json(self, ...):
    kafka_bootstrap, _, consumer_group_id = setup_test_containers_config(
        kafka_container,
        rabbitmq_container,
        monkeypatch,
        kafka_topic="events-empty-json-test",  # UNIQUE TOPIC
    )
    
    broker, rabbit_broker = initialize_production_bridge(
        async_session_factory,
        consumer_group_id=consumer_group_id,
        kafka_topic="events-empty-json-test",  # Pass through
    )
    
    # Publish to UNIQUE topic
    producer.produce("events-empty-json-test", value=json.dumps({}).encode())
```

## Architecture after fix

```
Topic "events-idempotency-test" contains:
└─ message B (ONLY from test_idempotency)

Consumer group "idempotency-test-group":
├─ Reads topic "events-idempotency-test"
└─ Sees: B (ONLY own message) ✓ ISOLATED

Topic "events-exception-nack-test" contains:
└─ message A (ONLY from test_exception_nack)

Consumer group "exception-nack-test-group":
├─ Reads topic "events-exception-nack-test"
└─ Sees: A (ONLY own message) ✓ ISOLATED
```

## Lessons

1. **Consumer group isolation ≠ message isolation**
   - Consumer groups only track offsets
   - All groups reading same topic see same messages

2. **Kafka topic is the actual message store**
   - Messages persist in topics
   - Multiple consumer groups share same topic data

3. **Both topic AND consumer group must be unique**
   - Unique consumer group alone insufficient
   - Unique topic provides true message isolation

4. **RabbitMQ exchange isolation insufficient for Kafka contamination**
   - Cross-contamination happens at Kafka level
   - RabbitMQ isolation applies after Kafka consumption

5. **Test cross-contamination symptoms are cryptic**
   - "Expected 1 got 2" doesn't reveal root cause
   - Need to inspect actual message content to identify source

## Files changed

**Test infrastructure**:
- `tests/integration/test_bridge_handler_integration/setup_helpers.py` - Added kafka_topic parameter

**Individual tests**:
- `tests/integration/test_bridge_handler_integration/test_idempotency.py` - Unique topic
- `tests/integration/test_bridge_handler_integration/test_exception_nack.py` - Unique topic
- `tests/integration/test_bridge_handler_integration/test_empty_json.py` - Unique topic
- `tests/unit/test_initialization_unit.py` - Mock signature fix (**kwargs)

## Verification

**Before fix** (commit f49de45):
```bash
pytest tests/integration/test_bridge_handler_integration/ -v
# FAILED: test_idempotency - AssertionError: assert 2 == 1
```

**After fix** (commit a8c4f20):
```bash
pytest tests/integration/test_bridge_handler_integration/ -v
# PASSED: All tests isolated
```

## Prevention

**Checklist for new Kafka integration tests**:
- [ ] Unique kafka_topic per test (most critical)
- [ ] Unique consumer_group_id per test
- [ ] Unique RabbitMQ exchange per test
- [ ] Unique queue names using uuid4()
- [ ] Test doesn't assume clean topic state
- [ ] Producer publishes to same unique topic

**Pattern**:
```python
@pytest.mark.integration
class TestMyFeature:
    async def test_scenario(self, ...):
        kafka_url, _, group_id = setup_test_containers_config(
            kafka_container,
            rabbitmq_container,
            monkeypatch,
            kafka_topic=f"events-my-feature-{uuid4()}",  # UNIQUE
            consumer_group_id=f"my-feature-{uuid4()}",   # UNIQUE
            exchange=f"test-events-my-feature-{uuid4()}", # UNIQUE
        )
        
        broker, _ = initialize_production_bridge(
            session_factory,
            consumer_group_id=group_id,
            kafka_topic=f"events-my-feature-{uuid4()}",  # UNIQUE
        )
        
        producer.produce(f"events-my-feature-{uuid4()}", ...)  # UNIQUE
```

## Related issues

- Consumer group isolation: kafka-consumer-group-test-isolation-bug.md
- Universal principles: integration-test-cross-contamination-bug.md
- AI lesson: kafka-topic-isolation-per-test.md
