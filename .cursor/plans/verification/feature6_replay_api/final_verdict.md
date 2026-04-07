# Feature 6: Replay API - All Sources Summary

## Feature Requirement
HTTP endpoint for time-range queries over outbox table, event republish by type and timestamp

## Kafka Native

### Capabilities
- ✅ **Consumer seek**: `consumer.seek(TopicPartition, offset)` - seek to specific offset
- ✅ **Offset reset to timestamp**: `consumer.offsetsForTimes()` - find offsets by timestamp
- ✅ **Replay from offset**: Consumer can reset to any offset and reprocess
- ❌ **No HTTP API**: This is client SDK functionality, not HTTP endpoint
- ❌ **No query by event type**: Kafka doesn't track event types, only offsets

### Verdict: **Partial coverage** - Kafka provides PRIMITIVES but not HTTP API

## Kafka Plugins

### Kafka Connect
- ⚠️ Connectors can rewind source offset
- ❌ No HTTP API for time-range replay
- ❌ Not applicable to our use case (we're not using Kafka Connect)

### Kafka Admin API
- ✅ Can reset consumer group offsets via Admin API
- ❌ No built-in "replay by type" or "replay by time range" endpoint
- ❌ Would require custom wrapper around Admin API

### Verdict: **NOT COVERED** - No HTTP API for event replay

## RabbitMQ Native

### Capabilities
- ❌ **No offset concept**: RabbitMQ uses ack/nack, not offsets
- ❌ **No time-travel**: Once message is ack'd, it's deleted
- ❌ **No replay**: Messages are consumed-and-deleted model
- ⚠️ **Queue inspection**: Can browse unacked messages (limited use)

### Verdict: **NOT COVERED** - RabbitMQ is not designed for replay

## RabbitMQ Plugins

### RabbitMQ Management HTTP API
- ✅ Can **inspect messages** in queue (limited to first N messages)
- ✅ Can **republish messages** from queue
- ❌ No **time-range queries** (no timestamp indexing)
- ❌ No **historical replay** (messages are deleted after ack)
- ❌ Limited to **current queue contents** only

### Verdict: **NOT COVERED** - Cannot replay historical messages

## FastStream

### Capabilities
- ✅ Broker utilities: `broker.start()`, `broker.stop()`, `broker.connect()`
- ❌ No replay utilities
- ❌ No offset management utilities
- ❌ No HTTP admin endpoints
- ❌ No time-range query helpers

### Verdict: **NOT COVERED** - FastStream doesn't provide replay features

## Our Use Case: Outbox Pattern

### Critical Insight
Our replay API operates on the **outbox table**, not Kafka/RabbitMQ directly:

```python
# Query outbox table by time + type
SELECT * FROM outbox 
WHERE event_type = 'user.created' 
  AND created_at BETWEEN :from_ts AND :to_ts
ORDER BY created_at
LIMIT :limit OFFSET :offset
```

Then **republish** events to Kafka/RabbitMQ.

### Why Libraries Don't Cover This
1. **Outbox is application-level**: Kafka/RabbitMQ don't know about our outbox table
2. **Event type filtering**: Kafka doesn't track event types in payload
3. **Time-range queries**: Requires database query, not broker query
4. **HTTP API**: Need FastAPI endpoint, not broker SDK

## Final Decision: **KEEP**

### Why KEEP
1. **Outbox-specific**: Replay queries our database outbox table
2. **Event type aware**: Filter by CloudEvents type field
3. **HTTP API**: Need REST endpoint for ops/debugging
4. **Business logic**: Decide which events to replay, apply rate limiting, etc.

### What We're NOT Duplicating
- ❌ NOT re-implementing Kafka `consumer.seek()` or `offsetsForTimes()`
- ❌ NOT re-implementing RabbitMQ management API
- ✅ **Implementing** HTTP API for **outbox table queries** + **republish logic**

### Implementation (Confirmed Correct)

```python
class OutboxReplayQueries:
    async def get_by_type_and_range(
        self, event_type: str, from_ts: datetime, to_ts: datetime
    ) -> list[IOutboxEvent]: ...

class OutboxReplayService:
    async def query(...) -> list[IOutboxEvent]: ...
    async def replay(...) -> int:  # returns count republished
        events = await self.queries.get_by_type_and_range(...)
        for event in events:
            await self.publisher.publish(event)  # Re-publish to Kafka/RabbitMQ
        return len(events)

# HTTP endpoint
@router.post("/replay")
async def replay_events(
    event_type: str | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
) -> dict[str, Any]: ...
```

### Use Cases
1. **Disaster recovery**: Replay events after downstream service failure
2. **Onboarding new consumers**: Replay historical events to new service
3. **Debugging**: Replay specific event type to reproduce issues
4. **Reprocessing**: Replay events after fixing bug in consumer logic

## Conclusion

**KEEP** - No library/plugin provides HTTP API for querying application-level outbox table and republishing events. This is custom business logic.
