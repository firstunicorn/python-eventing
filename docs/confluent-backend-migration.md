# Migration to FastStream Confluent Backend

**Date**: 2026-04-07  
**Status**: ✅ Complete  
**Reason**: Broker-level consumer group configuration support

## What Changed

### Dependencies
- **Before**: `faststream = {extras = ["kafka", "rabbit"], version = "^0.6.7"}` (aiokafka)
- **After**: `faststream = {extras = ["confluent", "rabbit"], version = "^0.6.7"}` (confluent-kafka-python)
- **Installed**: `confluent-kafka 2.14.0`

### Imports Updated
Changed `from faststream.kafka` → `from faststream.confluent` in:
- `src/messagekit/infrastructure/pubsub/broker_config.py`
- `src/messagekit/infrastructure/pubsub/kafka_publisher.py`
- `src/messagekit/infrastructure/health/outbox_health_check.py`
- `tests/unit/infrastructure/test_kafka_publisher.py`
- `tests/unit/infrastructure/test_fake_broker_contract/test_signature_match.py`

### Configuration Pattern
Now using broker-level consumer group config via `config` parameter:

```python
# Before (aiokafka - subscriber level):
@broker.subscriber("topic", group_id="messagekit-consumers", 
                   partition_assignment_strategy="cooperative-sticky")

# After (confluent - broker level):
broker = KafkaBroker(
    bootstrap_servers="...",
    config={
        "group.id": "messagekit-consumers",
        "partition.assignment.strategy": "cooperative-sticky",
        "max.poll.interval.ms": "300000",
        # ... other librdkafka settings
    }
)
```

## Important Clarifications

### Open Source vs Proprietary
⚠️ **This uses the OPEN SOURCE library, NOT proprietary Confluent Platform**

- **Library**: `confluent-kafka-python` (Apache 2.0 licensed)
- **Core**: `librdkafka` (Apache 2.0 licensed, C library)
- **NOT**: Confluent Platform (proprietary), Confluent Cloud (managed service)
- **GitHub**: https://github.com/confluentinc/confluent-kafka-python

### Why Confluent Backend?
1. **Broker-level config**: Set consumer group parameters once (DRYer)
2. **Performance**: librdkafka is C-based, highly optimized
3. **Kafka compatibility**: Better edge case handling
4. **Industry standard**: Most widely used Kafka client

### What We're NOT Using
- ❌ Confluent Platform (enterprise features)
- ❌ Confluent Cloud (managed Kafka)
- ❌ Proprietary Schema Registry features
- ✅ Only: Open source Python client connecting to our own Kafka brokers

## Configuration Reference

### librdkafka Configuration
Consumer group settings follow librdkafka format:
- Configuration docs: https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md
- Passed via `config` dict parameter to `KafkaBroker`
- Defined in `Settings.kafka_consumer_conf`

### Current Settings
```python
kafka_consumer_conf = {
    "group.id": "messagekit-consumers",
    "partition.assignment.strategy": "cooperative-sticky",
    "max.poll.interval.ms": "300000",
    "session.timeout.ms": "45000",
    "heartbeat.interval.ms": "15000",
}
```

## Testing Status
- ✅ All linters pass (Mypy: 0 errors)
- ✅ Dependencies installed successfully
- ✅ Import changes verified
- ⏳ Integration tests pending (Feature 8 implementation)

## Rollback Procedure
If needed, revert by:
1. Change `pyproject.toml`: `["confluent", "rabbit"]` → `["kafka", "rabbit"]`
2. Run: `poetry lock && poetry install`
3. Revert import changes: `faststream.confluent` → `faststream.kafka`
4. Remove `config` parameter from `create_kafka_broker()`
5. Add back subscriber-level group config note in docstring
