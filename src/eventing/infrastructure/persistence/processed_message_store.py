"""SQLAlchemy processed-message store for durable consumer idempotency."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Insert

from eventing.infrastructure.messaging import IProcessedMessageStore
from eventing.infrastructure.persistence.processed_message_orm import ProcessedMessageRecord


class SqlAlchemyProcessedMessageStore(IProcessedMessageStore):
    """Claim inbound event identifiers inside the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(self, *, consumer_name: str, event_id: str) -> bool:
        """Return whether this consumer may process the given event identifier."""
        if not consumer_name.strip():
            msg = "consumer_name must not be empty"
            raise ValueError(msg)
        if not event_id.strip():
            msg = "event_id must not be empty"
            raise ValueError(msg)
        if not self._session.in_transaction():
            await self._session.begin()
        statement = self._build_claim_statement(
            consumer_name=consumer_name,
            event_id=event_id,
        )
        try:
            result = await self._session.execute(statement)
        except IntegrityError as error:
            if self._is_duplicate_claim(error):
                return False
            raise
        rowcount = getattr(result, "rowcount", None)
        return isinstance(rowcount, int) and rowcount > 0

    def _build_claim_statement(self, *, consumer_name: str, event_id: str) -> Insert:
        values = {
            "consumer_name": consumer_name,
            "event_id": event_id,
            "processed_at": datetime.now(UTC),
        }
        table = cast(Table, ProcessedMessageRecord.__table__)
        dialect_name = self._session.get_bind().dialect.name
        if dialect_name == "postgresql":
            return cast(
                Insert,
                postgres_insert(table).values(**values).on_conflict_do_nothing(
                    index_elements=["consumer_name", "event_id"]
                ),
            )
        if dialect_name == "sqlite":
            return cast(
                Insert,
                sqlite_insert(table).values(**values).on_conflict_do_nothing(
                    index_elements=["consumer_name", "event_id"]
                ),
            )
        return table.insert().values(**values)

    @staticmethod
    def _is_duplicate_claim(error: IntegrityError) -> bool:
        message = str(error.orig).lower() if error.orig is not None else str(error).lower()
        return "duplicate" in message or "unique" in message
