"""Consume method implementation for idempotent Kafka consumers.

Extracted from IdempotentConsumerBase to keep the class definition concise
while preserving transaction management documentation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from messaging.infrastructure.pubsub.consumer_base.consumer_validators import extract_event_id

if TYPE_CHECKING:
    from messaging.infrastructure.pubsub.processed_message_store import (
        IProcessedMessageStore,
    )


async def consume_event(
    message: dict[str, Any],
    consumer_name: str,
    processed_message_store: IProcessedMessageStore,
    handle_event_coro: Any,
) -> bool:
    """Process a message once, returning whether work was performed.

    This method ensures idempotent processing by claiming the event_id
    before delegating to handle_event. If the event was already processed
    by this consumer, it returns False without calling handle_event.

    IMPORTANT: Transaction Management
    --------------------------------
    This method does NOT commit the transaction. The caller is responsible
    for committing or rolling back the session after this method returns.

    The transaction lifecycle is:
    1. claim() starts a transaction if not started
    2. handle_event() performs business logic in that transaction
    3. CALLER must commit on success or rollback on failure

    Example usage:
    ```python
    async with session_factory() as session:
        store = SqlAlchemyProcessedMessageStore(session)
        consumer = MyConsumer(store=store)

        was_processed = await consumer.consume(message)

        if was_processed:
            await session.commit()  # Commits both claim + business logic
        else:
            await session.rollback()  # Already processed, no work done
    ```

    Parameters
    ----------
    message : dict[str, Any]
        The deserialized message from Kafka, must contain eventId or event_id
    consumer_name : str
        Name of this consumer instance
    processed_message_store : IProcessedMessageStore
        Store used for idempotency tracking
    handle_event_coro : Any
        Coroutine function to call with the message (handle_event method)

    Returns
    -------
    bool
        True if the event was processed (handle_event was called)
        False if the event was already processed (duplicate, skipped)

    Raises
    ------
    ValueError
        If message is missing event_id or event_id is empty
    Exception
        Any exception raised by handle_event propagates to caller
    """
    event_id = extract_event_id(message)
    claimed = await processed_message_store.claim(
        consumer_name=consumer_name,
        event_id=event_id,
    )
    if not claimed:
        return False
    await handle_event_coro(message)
    return True
