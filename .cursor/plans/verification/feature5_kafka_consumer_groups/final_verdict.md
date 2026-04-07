# Feature 5: Kafka Consumer Groups - All Sources Summary

## Background
**Feature requirement**: Cooperative rebalancing, static membership, consumer group tuning via librdkafka config

## Kafka Native

### Findings (from Context7 + web search already done)
- ✅ **Fully supported** - Kafka natively supports consumer groups
- ✅ **Cooperative rebalancing**: `partition.assignment.strategy=cooperative-sticky` (default since Kafka 2.4+)
- ✅ **Static membership**: `group.instance.id` for avoiding unnecessary rebalances
- ✅ **All librdkafka configs**: Kafka consumer supports extensive configuration

### Key configs available
```python
group.id = "eventing-consumers"
group.instance.id = "eventing-1"  # Static membership
partition.assignment.strategy = "cooperative-sticky"
max.poll.interval.ms = 300000
session.timeout.ms = 45000
heartbeat.interval.ms = 15000
```

### Verdict: **FULLY SUPPORTED** by Kafka native

## Kafka Plugins

### Findings
- Kafka Streams also uses consumer groups
- Same configuration parameters apply
- No additional features beyond native Kafka consumer API

### Verdict: **Same as native Kafka**

## RabbitMQ

### N/A - RabbitMQ doesn't have Kafka-style consumer groups
- RabbitMQ uses **queues** and **exclusive consumers** instead
- Completely different architecture

### Verdict: **NOT APPLICABLE**

## FastStream (CRITICAL FINDING)

### Previous Deep Dive Findings
From `deep_dive_analysis_kafka_rabbitmq_faststream_parity.md`:

**FastStream KafkaBroker `conf` parameter accepts arbitrary librdkafka configuration**:

```python
broker = KafkaBroker("localhost:9092", conf=[
    ("group.id", "eventing-consumers"),
    ("group.instance.id", "eventing-1"),
    ("partition.assignment.strategy", "cooperative-sticky"),
    ("max.poll.interval.ms", "300000"),
    ("session.timeout.ms", "45000"),
    ("heartbeat.interval.ms", "15000"),
])
```

### What this means
- ✅ **ALL librdkafka configs** are accessible via `conf` parameter
- ✅ No need for FastStream to expose individual configuration properties
- ✅ Generic interface: FastStream passes configs directly to librdkafka
- ✅ Future-proof: New librdkafka configs automatically supported

### Verdict: **FULLY SIMPLIFIED**

## Final Decision: **SIMPLIFY (Already Done in Plan)**

### What Was Already Simplified

**Original approach** (hypothetical complexity):
- Create 6 individual `Settings` fields:
  ```python
  kafka_group_id: str
  kafka_group_instance_id: str | None
  kafka_partition_strategy: str
  kafka_max_poll_interval_ms: int
  kafka_session_timeout_ms: int
  kafka_heartbeat_interval_ms: int
  ```
- Map each field to FastStream `KafkaBroker` constructor

**Simplified approach** (current plan):
- Single field:
  ```python
  kafka_consumer_conf: dict[str, str] = Field(
      default_factory=lambda: {
          "group.id": "eventing-consumers",
          "partition.assignment.strategy": "cooperative-sticky",
          "max.poll.interval.ms": "300000",
          ...
      }
  )
  ```
- Pass directly to FastStream via `conf`:
  ```python
  conf_list = [(k, v) for k, v in settings.kafka_consumer_conf.items()]
  broker = KafkaBroker(..., conf=conf_list)
  ```

### Benefits of Current Approach

1. **Fewer Settings fields**: 1 dict instead of 6 individual fields
2. **More flexible**: Any librdkafka config can be added without code changes
3. **Future-proof**: New Kafka consumer configs supported automatically
4. **Less boilerplate**: No need to map individual fields to broker constructor
5. **Environment variable friendly**: Can pass as JSON string

## Comparison to Alternatives

### Alternative: Individual Settings Fields (Rejected)
**Pros**: Type safety, explicit configuration
**Cons**: Code bloat, inflexible, requires updates for new Kafka configs

### Current: Dict-based Config (Chosen)
**Pros**: Flexible, future-proof, minimal code, follows FastStream conventions
**Cons**: Less type safety (could validate with Pydantic if needed)

## Implementation Status

**ALREADY SIMPLIFIED** in main plan:
- Feature 5 description already uses dict-based approach
- Code examples already show `conf` parameter usage
- Settings field already defined as single `kafka_consumer_conf: dict[str, str]`

## Test Strategy (Remains Same)

```python
# Integration test
def test_static_membership_survives_restart():
    # Consumer with group.instance.id survives restart without rebalance
    ...

def test_cooperative_sticky_assignment():
    # Two consumers with same group.id consume disjoint partitions
    # No full revocation on rebalance
    ...
```

## Conclusion

**ALREADY SIMPLIFIED** - The current plan already uses FastStream's `conf` parameter for generic librdkafka configuration. No further simplification needed.

**Feature Status**: **KEEP AS-IS** (already simplified from original 6 fields to 1 dict)
