# Consumer transaction management guide

**API Reference:** [IdempotentConsumerBase](https://python-eventing.readthedocs.io/en/latest/autoapi/messaging/infrastructure/messaging/kafka_consumer_base/index.html)

**Integration Guide:** [Consume idempotently](https://python-eventing.readthedocs.io/en/latest/integration-guide.html#consume-idempotently)

## Overview

This document clarifies transaction boundaries and responsibilities for Kafka consumers
using the idempotent consumer pattern with processed-message store.

## Transaction lifecycle

### The pattern

The idempotent consumer follows this transaction pattern:

```
1. START transaction (if not started)
2. CLAIM event_id (insert into processed_messages)
3. HANDLE event (business logic)
4. COMMIT transaction (caller's responsibility)
```

### Key responsibilities

| Component | Responsibility |
|-----------|----------------|
| **ProcessedMessageStore** | Start transaction if needed, claim event_id |
| **ConsumerBase** | Orchestrate claim + handle |
| **Concrete Consumer** | Implement handle_event, provide session |
| **Caller/Framework** | **COMMIT or ROLLBACK** the session |

## Critical: caller must commit

**IMPORTANT:** The `SqlAlchemyProcessedMessageStore.claim()` method starts a transaction
but **DOES NOT** commit it. The caller **MUST** commit the session after successful
processing, or rollback on failure.

### Why this design?

This design ensures atomicity between:
1. Marking the event as processed (claim)
2. The business logic side effects (handle_event)

If either fails, both should roll back together.

## Correct usage

### Pattern 1: with FastStream consumer

```python
from faststream.kafka import KafkaBroker
from messaging.infrastructure.messaging.kafka_consumer_base import IdempotentConsumerBase
from messaging.infrastructure.persistence.processed_message_store import SqlAlchemyProcessedMessageStore

broker = KafkaBroker()

class MyConsumer(IdempotentConsumerBase):
    def __init__(self, session_factory):
        self._session_factory = session_factory
        # Consumer will create session per message

    async def handle_event(self, message: dict) -> None:
        """Process the event (business logic)."""
        # Business logic here
        await process_business_logic(message)

@broker.subscriber("my-topic")
async def consume_message(message: dict) -> None:
    """Consume one Kafka message with idempotency and transactionality."""
    async with session_factory() as session:
        # 1. Create store with session
        store = SqlAlchemyProcessedMessageStore(session)

        # 2. Create consumer with store
        consumer = MyConsumer(store)

        # 3. Process message (starts transaction, claims, handles)
        was_processed = await consumer.consume(message)

        if was_processed:
            # 4. COMMIT if processing succeeded
            await session.commit()
            logger.info("Message %s processed and committed", message["event_id"])
        else:
            # 5. ROLLBACK if already processed (idempotent skip)
            await session.rollback()
            logger.debug("Message %s already processed, skipped", message["event_id"])

        # FastStream will ACK the Kafka message after this function returns
```

### Pattern 2: explicit transaction control

```python
async def process_one_event(event: dict) -> None:
    """Process one event with explicit transaction management."""
    async with session_factory() as session:
        try:
            # Create store bound to this session
            store = SqlAlchemyProcessedMessageStore(session)
            consumer = MyConsumer(store)

            # Attempt to claim and process
            was_processed = await consumer.consume(event)

            if was_processed:
                # Commit on success
                await session.commit()
            else:
                # Already processed - rollback claim attempt
                await session.rollback()

        except Exception as exc:
            # Error during processing - rollback everything
            logger.error("Failed to process event: %s", exc, exc_info=True)
            await session.rollback()
            raise
```

## Transaction guarantees

### Success case

```
START transaction
  ↓
CLAIM event_id (INSERT processed_messages)
  ↓
HANDLE event (business logic)
  ↓
COMMIT
  ↓
Both claim + business logic committed atomically
```

### Failure during handle

```
START transaction
  ↓
CLAIM event_id (INSERT processed_messages)
  ↓
HANDLE event → EXCEPTION
  ↓
ROLLBACK
  ↓
Neither claim nor business logic persisted
Event will be reprocessed on next attempt
```

### Duplicate message (already claimed)

```
START transaction
  ↓
CLAIM event_id → False (already processed)
  ↓
ROLLBACK (nothing to commit)
  ↓
No work performed, message ACKed as duplicate
```

## Common pitfalls

### Pitfall 1: forgetting to commit

```python
# ❌ WRONG: Transaction never committed
async def bad_consumer(message: dict) -> None:
    async with session_factory() as session:
        store = SqlAlchemyProcessedMessageStore(session)
        consumer = MyConsumer(store)
        await consumer.consume(message)
        # Missing: await session.commit()
        # Result: Transaction rolled back, event will be reprocessed infinitely
```

### Pitfall 2: committing before handle completes

```python
# ❌ WRONG: Commits claim but not business logic
async def bad_consumer(message: dict) -> None:
    async with session_factory() as session:
        store = SqlAlchemyProcessedMessageStore(session)

        # Claim in transaction
        claimed = await store.claim(consumer_name="test", event_id=message["event_id"])
        await session.commit()  # ❌ Commits too early!

        if claimed:
            # Business logic in NEW transaction or no transaction
            await handle_business_logic(message)  # ❌ Not atomic with claim!
```

### Pitfall 3: sharing session across messages

```python
# ❌ WRONG: Single session for multiple messages
async def bad_batch_consumer(messages: list[dict]) -> None:
    async with session_factory() as session:  # ❌ One session for all
        store = SqlAlchemyProcessedMessageStore(session)
        consumer = MyConsumer(store)

        for message in messages:
            await consumer.consume(message)

        await session.commit()  # ❌ All-or-nothing for entire batch
        # Result: One failure rolls back all successful processing
```

**Correct approach:** One session per message:
```python
# ✅ CORRECT: Separate session per message
async def good_batch_consumer(messages: list[dict]) -> None:
    for message in messages:
        async with session_factory() as session:  # ✅ New session each time
            store = SqlAlchemyProcessedMessageStore(session)
            consumer = MyConsumer(store)

            was_processed = await consumer.consume(message)
            if was_processed:
                await session.commit()  # ✅ Independent commit
            else:
                await session.rollback()
```

## Testing transaction boundaries

### Test atomicity

```python
async def test_claim_and_handle_atomic():
    """Verify claim + handle are atomic (both commit or both rollback)."""
    async with session_factory() as session:
        store = SqlAlchemyProcessedMessageStore(session)
        consumer = FailingConsumer(store)  # Raises in handle_event

        with pytest.raises(Exception):
            await consumer.consume(message)

        # Don't commit (simulating error case)
        await session.rollback()

    # Verify claim was rolled back (event can be reprocessed)
    async with session_factory() as session:
        store = SqlAlchemyProcessedMessageStore(session)
        # Should be able to claim again
        claimed = await store.claim(consumer_name="test", event_id=message["event_id"])
        assert claimed is True  # ✅ Not marked as processed
```

### Test idempotency

```python
async def test_duplicate_handling():
    """Verify duplicate messages are skipped."""
    # First processing
    async with session_factory() as session:
        store = SqlAlchemyProcessedMessageStore(session)
        consumer = MyConsumer(store)
        was_processed = await consumer.consume(message)
        assert was_processed is True
        await session.commit()

    # Second processing (duplicate)
    async with session_factory() as session:
        store = SqlAlchemyProcessedMessageStore(session)
        consumer = MyConsumer(store)
        was_processed = await consumer.consume(message)
        assert was_processed is False  # ✅ Skipped as duplicate
        await session.rollback()
```

## Integration with Kafka

### Kafka message acknowledgment

The transaction commit should happen **before** Kafka ACK:

```
1. Consume Kafka message
2. START DB transaction
3. CLAIM + HANDLE in transaction
4. COMMIT DB transaction  ← Must succeed
5. ACK Kafka message     ← Only after DB commit
```

If DB commit fails, Kafka message is NOT ACKed, and will be redelivered.

### With FastStream

FastStream automatically ACKs after the handler returns successfully:

```python
@broker.subscriber("topic")
async def handler(message: dict) -> None:
    async with session_factory() as session:
        store = SqlAlchemyProcessedMessageStore(session)
        consumer = MyConsumer(store)
        await consumer.consume(message)
        await session.commit()  # Must succeed
    # FastStream ACKs here (after successful return)
```

If `session.commit()` raises an exception:
- Handler raises exception
- FastStream does NOT ACK
- Kafka redelivers message
- Consumer will retry (hopefully transiently)

## Summary

| Responsibility | Owner |
|---------------|-------|
| Start transaction if needed | ProcessedMessageStore.claim() |
| Claim event_id | ProcessedMessageStore.claim() |
| Business logic | Concrete consumer (handle_event) |
| **COMMIT or ROLLBACK** | **Caller** (FastStream handler, etc.) |
| ACK Kafka message | Framework (FastStream) after successful return |

**Golden Rule:** The component that creates the session is responsible for committing or rolling it back.

**Critical:** Never let a transaction end without explicit commit or rollback. Use try/except/finally to ensure cleanup.
