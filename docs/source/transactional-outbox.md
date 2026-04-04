# Transactional outbox pattern - usage guide

**Full documentation:** [Integration Guide - Publish through the outbox](https://python-eventing.readthedocs.io/en/latest/integration-guide.html#publish-through-the-outbox)

## Overview

Use `OutboxRepository.add_event()` with an external session to ensure events are committed atomically with your business data.

The transactional outbox pattern ensures that domain events and business data are committed atomically in a single database transaction. This prevents the dual-write problem where:
1. Business data is committed
2. Application crashes before event is stored
3. Event is lost → inconsistency

## Correct usage

### With external session (transactional outbox)

**This is the recommended pattern for production use:**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository
from your_app.domain import YourBusinessRepository

# Setup (once at app startup)
session_factory: async_sessionmaker[AsyncSession] = create_session_factory(db_url)
outbox_repo = SqlAlchemyOutboxRepository(session_factory, registry)
business_repo = YourBusinessRepository()

# In your use case / command handler:
async def create_invite_handler(command: CreateInviteCommand) -> None:
    """Create invite with guaranteed event delivery."""
    async with session_factory() as session:
        # 1. Business write (uses session)
        invite = await business_repo.create(command.data, session=session)

        # 2. Create domain event
        event = InviteCreatedEvent(
            invite_id=invite.id,
            email=invite.email,
            occurred_at=datetime.now(UTC),
        )

        # 3. Add event to outbox (SAME session, NO commit)
        await outbox_repo.add_event(event, session=session)

        # 4. Single atomic commit (business data + event)
        await session.commit()

    # ✅ Both invite AND event are committed atomically
    # ✅ If commit fails, both are rolled back
    # ✅ Zero risk of event loss
```

### Without external session (standalone mode)

**Only use this for testing or when business data doesn't need atomicity:**

```python
# Add event with auto-commit (not transactional with business logic)
async def log_system_event() -> None:
    event = SystemStartedEvent(occurred_at=datetime.now(UTC))
    await outbox_repo.add_event(event)  # Creates session, commits immediately
```

## Anti-pattern (dual write problem)

**❌ DO NOT DO THIS:**

```python
async def create_invite_handler_WRONG(command: CreateInviteCommand) -> None:
    # Separate transactions = NOT ATOMIC
    async with session_factory() as session:
        invite = await business_repo.create(command.data, session=session)
        await session.commit()  # ❌ First commit

    # ⚠️ App can crash here → event lost

    event = InviteCreatedEvent(...)
    await outbox_repo.add_event(event)  # ❌ Second commit (separate transaction)
```

**Why this usage of the library is wrong:**
- Two separate commits = not atomic
- If second commit fails, business data exists but no event
- If app crashes between commits, event is lost
- Database and event stream become inconsistent

## Key points

1. **Pass `session` parameter** to `add_event()` for transactional outbox
2. **Single `commit()`** for both business data and event
3. **Same session** must be used for both operations
4. **Caller controls commit**, not the repository

## Testing

### Test atomicity

```python
async def test_outbox_rollback():
    """Verify event is rolled back if business operation fails."""
    async with session_factory() as session:
        await business_repo.create(data, session=session)
        await outbox_repo.add_event(event, session=session)
        await session.rollback()  # Simulate failure

    # Both business data and event should NOT exist
    assert await business_repo.exists(data.id) is False
    assert await outbox_repo.count_unpublished() == 0
```

### Test independent commit

```python
async def test_outbox_standalone_mode():
    """Verify standalone mode works for non-transactional cases."""
    event = TestEvent()
    await outbox_repo.add_event(event)  # No session = auto-commit

    # Event should exist immediately
    assert await outbox_repo.count_unpublished() == 1
```

## Background worker

The outbox worker polls for unpublished events and publishes them:

```python
# Worker runs independently, publishes events from outbox
worker = ScheduledOutboxWorker(repository, publisher, config)
await worker.schedule_publishing()  # Polls every N seconds
```

The pattern ensures:
1. **Atomicity**: Business data + event committed together
2. **Durability**: Events stored in database before publishing
3. **Retry**: Worker retries failed publishes with exponential backoff
4. **Observability**: Repository tracks published/failed status
