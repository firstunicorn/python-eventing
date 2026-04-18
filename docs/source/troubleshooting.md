# Troubleshooting

Common issues and solutions for `python-eventing` integration.

## Events stuck in outbox (not publishing)

**Symptoms:**
- Events persist to `outbox_events` table
- `published` flag remains `false`
- No events appearing in Kafka topics

**Solutions:**
1. Verify Kafka Connect Debezium connector is running:
   ```bash
   curl http://localhost:8083/connectors/outbox-connector/status
   ```

2. Check CDC connector configuration points to outbox table:
   ```json
   {
     "table.include.list": "public.outbox_events",
     "transforms": "outbox",
     "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter"
   }
   ```

3. Review Kafka Connect logs for CDC errors:
   ```bash
   docker logs kafka-connect
   ```

4. Verify database permissions for Debezium user

## Duplicate messages consumed

**Symptoms:**
- Same event processed multiple times
- Idempotent consumer not preventing duplicates

**Solutions:**
1. Ensure `IProcessedMessageStore` is configured in consumer:
   ```python
   from messaging.infrastructure import IdempotentConsumerBase

   class MyConsumer(IdempotentConsumerBase):
       def __init__(self, store: IProcessedMessageStore):
           super().__init__(store)
   ```

2. Verify `processed_messages` table exists and is populated

3. Check consumer is using transactional session for store operations

4. Review Kafka consumer group configuration (enable.auto.commit=false)

## Health check failures

**Symptoms:**
- `/health` endpoint returns unhealthy status
- Outbox health check failing

**Solutions:**
1. Check outbox table has unpublished events older than threshold:
   ```sql
   SELECT COUNT(*) FROM outbox_events
   WHERE published = false
   AND created_at < NOW() - INTERVAL '5 minutes';
   ```

2. Verify Kafka Connect CDC is processing changes

3. Review FastStream broker health endpoint configuration

4. Check database connection pool exhaustion

## Import errors

**Symptom:**
```python
ModuleNotFoundError: No module named 'eventing'
```

**Solution:**
The import package is `messaging`, not `eventing`:
```python
# Correct
from messaging.core import BaseEvent

# Incorrect
from eventing.core import BaseEvent  # ❌
```

The PyPI distribution name is `python-eventing`, but imports use `messaging`.

## Performance issues

**Symptoms:**
- Slow outbox writes
- High database load

**Solutions:**
1. Add database indexes on outbox table (see Setup section)

2. Tune Debezium CDC polling interval:
   ```json
   {
     "poll.interval.ms": "500"
   }
   ```

3. Increase Kafka Connect worker threads

4. Review SQLAlchemy connection pool settings

5. Consider partitioning outbox table by created_at for high volume

## Further assistance

- Review [Integration Guide](integration-guide.html) for setup verification
- Check [Debezium CDC Architecture](debezium-cdc-architecture.html) for publishing details
- See [Consumer Transactions](consumer-transactions.html) for idempotency patterns
- [Open issue on GitHub](https://github.com/firstunicorn/python-eventing/issues)
