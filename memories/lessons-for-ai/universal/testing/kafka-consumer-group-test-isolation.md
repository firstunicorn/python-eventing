# Kafka consumer group test isolation

**[Rule](#rule)** • **[Implementation](#implementation)** • **[Pattern](#pattern)**

## Rule

Integration tests sharing Kafka topics MUST use unique consumer group IDs. Shared groups cause message cross-contamination.

## Critical implementation

**Make consumer_group_id configurable**:

```python
# 1. Add to config dataclass
@dataclass
class BridgeConfig:
    kafka_topic: str
    consumer_group_id: str  # Not hardcoded

# 2. Pass to subscriber decorator
@broker.subscriber(
    config.kafka_topic,
    group_id=config.consumer_group_id,  # Use from config, not hardcoded
)
async def handler(message):
    pass

# 3. Per-test unique ID
def test_my_scenario():
    config = BridgeConfig(
        kafka_topic="events",
        consumer_group_id=f"my-test-{uuid4()}"  # UNIQUE per test
    )
```

## Why shared groups fail

Kafka consumer groups maintain **shared offset state**:

1. Test A publishes to "events" topic
2. Test A uses group "my-consumers"  
3. Test B also uses group "my-consumers" (SAME)
4. Test B receives Test A's unconsumed messages + own messages
5. Assertion fails: expected 1 message, got 2+

## Pattern

**Test setup helper**:
```python
def setup_test_containers_config(
    kafka_container,
    rabbitmq_container,
    monkeypatch,
    consumer_group_id: str = f"test-{uuid4()}",  # Unique default
) -> tuple[str, str, str]:
    """Returns: (kafka_url, rabbit_url, consumer_group_id)"""
    kafka_bootstrap = kafka_container.get_bootstrap_server()
    rabbitmq_url = rabbitmq_container.get_connection_url()
    
    monkeypatch.setattr(settings, "kafka_bootstrap_servers", kafka_bootstrap)
    
    return kafka_bootstrap, rabbitmq_url, consumer_group_id
```

**Per-test usage**:
```python
@pytest.mark.integration
async def test_idempotency(kafka_container, ...):
    _, _, group_id = setup_test_containers_config(
        kafka_container,
        rabbitmq_container,
        monkeypatch,
        consumer_group_id="idempotency-test-unique"  # UNIQUE
    )
    
    broker = initialize_broker(consumer_group_id=group_id)
```

## Prevention checklist

Before creating Kafka integration test:
- [ ] consumer_group_id configurable (not hardcoded)
- [ ] Per-test unique group ID passed
- [ ] Test doesn't assume clean topic state
- [ ] Setup helper returns group_id for verification
- [ ] All infrastructure IDs unique (exchange, queue, group)

## Error symptom

```python
AssertionError: assert 2 == 1
  where 2 = len([message_from_other_test, my_test_message])
```

Test receives unexpected messages from other tests = shared consumer group.
