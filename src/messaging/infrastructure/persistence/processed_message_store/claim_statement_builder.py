"""Dialect-specific claim statement builders.

Generates INSERT ... ON CONFLICT DO NOTHING statements targeting the
processed_message_record table, adapted for PostgreSQL, SQLite, or generic
SQLAlchemy dialects.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Insert

from messaging.infrastructure.persistence.orm_models.processed_message_orm import (
    ProcessedMessageRecord,
)


def build_claim_statement(
    session: AsyncSession,
    *,
    consumer_name: str,
    event_id: str,
) -> Insert:
    """Build dialect-specific INSERT ... ON CONFLICT DO NOTHING statement.

    Uses database-specific ON CONFLICT DO NOTHING to handle races gracefully.
    PostgreSQL uses postgres_insert with unique constraint index, SQLite uses
    sqlite_insert with the same pattern, and fallback works with generic insert.

    Args:
        session (AsyncSession): SQLAlchemy async session to determine the database dialect
        consumer_name (str): Name of the consumer claiming the event
        event_id (str): Unique identifier of the event

    Returns:
        Insert: Dialect-specific INSERT statement with on_conflict_do_nothing

    Raises:
        RuntimeError: If database dialect is not supported (not PostgreSQL or SQLite)
    """
    values = {
        "consumer_name": consumer_name,
        "event_id": event_id,
        "processed_at": datetime.now(UTC),
    }
    table = cast(Table, ProcessedMessageRecord.__table__)
    dialect_name = session.get_bind().dialect.name
    if dialect_name == "postgresql":
        return cast(
            Insert,
            postgres_insert(table)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["consumer_name", "event_id"]),
        )
    if dialect_name == "sqlite":
        return cast(
            Insert,
            sqlite_insert(table)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["consumer_name", "event_id"]),
        )
    msg = (
        f"Unsupported database dialect: {dialect_name!r}. "
        "Only postgresql and sqlite are supported for ON CONFLICT DO NOTHING."
    )
    raise RuntimeError(msg)
