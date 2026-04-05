"""SQLAlchemy processed-message store for durable consumer idempotency.

This module provides the `SqlAlchemyProcessedMessageStore` which implements
the `IProcessedMessageStore` protocol using SQLAlchemy. It attempts to insert a
record for a given event and consumer, returning True if successful (meaning the
event hasn't been processed yet) and False if the record already exists.

See Also
--------
- messaging.infrastructure.persistence.processed_message_orm : The underlying ORM model
- messaging.infrastructure.pubsub.kafka_consumer_base : The consumer that uses this store
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from messaging.infrastructure.persistence.processed_message_store.claim_helpers import (
    build_claim_statement,
    is_duplicate_claim,
)
from messaging.infrastructure.pubsub import IProcessedMessageStore


class SqlAlchemyProcessedMessageStore(IProcessedMessageStore):
    """Claim inbound event identifiers inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(self, *, consumer_name: str, event_id: str) -> bool:
        """Return whether this consumer may process the given event identifier.

        This method attempts to insert a record claiming this event for this consumer.
        It uses database-specific ON CONFLICT DO NOTHING to handle races gracefully.

        IMPORTANT: Transaction Management
        --------------------------------
        This method starts a transaction if one is not active, but does NOT commit it.
        The caller is responsible for committing the transaction after successful
        business logic, or rolling back on failure.

        Transaction lifecycle:
        1. START transaction if not active (this method)
        2. INSERT claim record (this method)
        3. [Business logic in caller's code]
        4. COMMIT or ROLLBACK (caller's responsibility)

        This design ensures atomicity between the claim and business logic side effects.

        Args:
            consumer_name (str): Name of the consumer claiming the event
                (must not be empty)
            event_id (str): Unique identifier of the event (must not be empty)

        Returns:
            bool: True if the event was claimed (first processing attempt),
                False if the event was already claimed (duplicate, idempotent skip).

        Raises:
            ValueError: If consumer_name or event_id is empty.
            IntegrityError: If a database constraint is violated (non-duplicate case).
        """
        if not consumer_name.strip():
            msg = "consumer_name must not be empty"
            raise ValueError(msg)
        if not event_id.strip():
            msg = "event_id must not be empty"
            raise ValueError(msg)

        # Start transaction if not active (caller will commit/rollback later)
        if not self._session.in_transaction():
            await self._session.begin()

        statement = build_claim_statement(
            session=self._session,
            consumer_name=consumer_name,
            event_id=event_id,
        )
        try:
            result = await self._session.execute(statement)
        except IntegrityError as error:
            if is_duplicate_claim(error):
                return False  # Already processed by this consumer
            raise  # Other integrity error (unexpected)

        rowcount = getattr(result, "rowcount", None)
        return isinstance(rowcount, int) and rowcount > 0
