# Feature 9: DLQ Admin API - All Sources Summary

## Feature Requirement
HTTP endpoints for failed message inspection, retry, manual intervention

## Kafka Native

### DLQ Pattern
- ✅ **Dead letter topic pattern**: Convention to publish failed messages to `-dlq` topic
  ```python
  try:
      process_message(msg)
  except Exception:
      await producer.send("events-dlq", msg)
  ```
- ⚠️ **Application-level**: Not enforced by Kafka broker
- ❌ **No HTTP API**: No built-in admin interface
- ❌ **No inspection tools**: Must consume from DLQ topic manually

### Verdict: **PATTERN exists, ADMIN API does not**

## Kafka Plugins

### Kafka Connect DLQ
- ✅ **Connect error handling**: Kafka Connect can route failed messages to DLQ topic
- ⚠️ **Connect-specific**: Only for Kafka Connect connectors
- ❌ **No HTTP API**: No admin interface for DLQ management
- ❌ **Not applicable**: We're not using Kafka Connect

### Verdict: **NOT APPLICABLE** to our use case

## RabbitMQ Native

### Dead Letter Exchange (DLX)
- ✅ **DLX built-in**: Messages rejected/expired go to configured DLX
  ```python
  channel.queue_declare(
      queue="work-queue",
      arguments={"x-dead-letter-exchange": "dlx"}
  )
  ```
- ✅ **Automatic**: RabbitMQ routes failed messages automatically
- ❌ **No inspection API**: No built-in admin interface for DLX
- ❌ **No retry API**: Must manually republish from DLX

### Verdict: **PATTERN exists, ADMIN API does not**

## RabbitMQ Plugins

### RabbitMQ Management HTTP API
- ✅ **Queue inspection**: GET `/api/queues/{vhost}/{queue}/get` - get messages from queue
- ✅ **Message details**: Returns message properties, payload, routing info
- ✅ **Republish**: Can publish messages via POST `/api/exchanges/{vhost}/{exchange}/publish`
- ⚠️ **Generic API**: Not DLQ-specific, works for any queue
- ⚠️ **Limited**: Can only get first N messages (not full query capability)
- ⚠️ **No filtering**: Cannot filter by error type, timestamp range, etc.

### Example
```bash
# Get messages from DLQ
curl -u guest:guest http://localhost:15672/api/queues/%2F/dlq/get \
  -d '{"count":10,"ackmode":"ack_requeue_false","encoding":"auto"}'

# Republish
curl -u guest:guest http://localhost:15672/api/exchanges/%2F/events/publish \
  -d '{"properties":{},"routing_key":"events","payload":"...","payload_encoding":"string"}'
```

### Verdict: **Partial coverage** - Generic queue API, not DLQ-specific admin interface

## FastStream

### Existing DLQ Support
From our codebase analysis:
- ✅ `IdempotentConsumerBase`: Tracks processed messages
- ✅ `SqlAlchemyProcessedMessageStore`: Stores processing state in database
- ✅ DLQ handling: Failed messages can be routed to dead letter topic/queue

### What's Missing
- ❌ **No HTTP API**: No admin endpoints for DLQ inspection
- ❌ **No retry utilities**: No built-in retry mechanism
- ❌ **No filtering**: No query by error type, timestamp, etc.

### Verdict: **DLQ mechanism exists, HTTP ADMIN API does not**

## Our Requirements

### Why Generic APIs Don't Fit

**RabbitMQ Management API limitations**:
1. Generic queue API, not DLQ-aware
2. Cannot filter by error metadata (error type, retry count, etc.)
3. Cannot query by time range
4. No batch retry operation
5. No integration with our outbox pattern

**Our needs**:
1. **Query failed events**: Filter by event type, error type, timestamp range
2. **Inspect error details**: See error message, stack trace, retry count
3. **Retry mechanism**: Republish failed events (single or batch)
4. **Audit trail**: Track who retried which messages
5. **Integration**: Works with our outbox + DLQ tables

## Final Decision: **KEEP**

### Why KEEP
1. **Outbox-specific**: Our DLQ is in database, not just Kafka/RabbitMQ topic
2. **Rich queries**: Filter by event type, error type, timestamp, retry count
3. **HTTP API**: REST endpoints for ops/debugging
4. **Business logic**: Decide which messages to retry, apply rate limiting, validate before retry
5. **Audit trail**: Log retry operations for compliance

### What We're NOT Duplicating
- ❌ NOT re-implementing Kafka DLQ topic pattern (already exists)
- ❌ NOT re-implementing RabbitMQ DLX (already exists)
- ❌ NOT re-implementing RabbitMQ Management API (too generic)
- ✅ **Implementing**: HTTP admin API for **outbox DLQ table** with rich queries

### Implementation (Confirmed Correct)

**Our plan** already extends existing DLQ infrastructure:

```python
# Existing (from codebase)
class IdempotentConsumerBase:
    async def process_with_dlq(self, msg) -> None:
        try:
            await self.process(msg)
        except Exception as e:
            await self.send_to_dlq(msg, error=str(e))

# New: Admin queries
class OutboxDLQQueries:
    async def get_failed_events(
        self, event_type: str | None, error_type: str | None,
        from_ts: datetime | None, limit: int
    ) -> list[FailedEvent]: ...

# New: HTTP API
@router.get("/dlq")
async def list_failed_events(
    event_type: str | None = None,
    error_type: str | None = None,
    from_ts: datetime | None = None,
) -> list[dict]: ...

@router.post("/dlq/retry")
async def retry_failed_events(
    event_ids: list[str]
) -> dict[str, Any]:
    # Validate, republish, update DLQ status
    ...
```

### Use Cases
1. **Debugging**: Inspect failed messages to understand error patterns
2. **Manual intervention**: Retry messages after fixing downstream issue
3. **Poison pill handling**: Identify and skip permanently broken messages
4. **Monitoring**: Query recent failures for alerting
5. **Audit**: Track who retried which messages when

### Comparison to RabbitMQ Management API

| Feature | RabbitMQ Mgmt API | Our DLQ Admin API | Winner |
|---------|------------------|------------------|--------|
| Queue inspection | ✅ Generic | ✅ DLQ-specific | ✅ Ours |
| Filter by event type | ❌ No | ✅ Yes | ✅ Ours |
| Filter by error type | ❌ No | ✅ Yes | ✅ Ours |
| Time-range queries | ❌ No | ✅ Yes | ✅ Ours |
| Batch retry | ❌ Manual | ✅ Built-in | ✅ Ours |
| Audit trail | ❌ No | ✅ Yes | ✅ Ours |
| Integration | ❌ Generic | ✅ Outbox-aware | ✅ Ours |

## Conclusion

**KEEP** - RabbitMQ Management API provides generic queue operations but not DLQ-specific admin interface with rich queries and retry logic. Our custom HTTP API fills this gap.

**Implementation approach**: Extend existing `IdempotentConsumerBase` and DLQ handling with HTTP admin endpoints for inspection, filtering, and retry operations.
