"""Shared pytest configuration for eventing tests."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

import pytest
from hypothesis import HealthCheck, settings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from eventing.infrastructure.persistence.orm_base import Base


def _configure_hypothesis_profiles() -> None:
    """Register the supported Hypothesis profiles for local and CI runs."""
    common = settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    settings.register_profile("default", common)
    settings.register_profile(
        "thorough",
        settings(max_examples=1000, parent=common),
    )
    settings.register_profile(
        "stress",
        settings(max_examples=100000, parent=common),
    )
    settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "thorough"))


@lru_cache(maxsize=1)
def _docker_available() -> bool:
    """Return whether Docker is reachable from the current test environment."""
    docker_binary = shutil.which("docker")
    if docker_binary is None:
        return False
    result = subprocess.run(  # noqa: S603
        [docker_binary, "version", "--format", "{{.Server.Version}}"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return result.returncode == 0


def pytest_configure(config: pytest.Config) -> None:
    """Configure shared test settings once per test session."""
    _ = config
    _configure_hypothesis_profiles()


@pytest.fixture(scope="session")
def docker_or_skip() -> None:
    """Skip container-based tests when Docker is not available."""
    if not _docker_available():
        pytest.skip("Docker is unavailable in this environment")


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
