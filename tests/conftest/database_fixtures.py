"""Database fixtures for testing."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from messaging.infrastructure.persistence.orm_models.orm_base import Base


@pytest.fixture
async def sqlite_session_factory(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]]]:
    """Create a temporary SQLite-backed async session factory for integration tests."""
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'eventing.db'}"
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield engine, factory
    await engine.dispose()


@pytest.fixture
def skip_broker_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip broker connection for HTTP-only unit/integration tests."""
    monkeypatch.setenv("TESTING_SKIP_BROKER", "true")
