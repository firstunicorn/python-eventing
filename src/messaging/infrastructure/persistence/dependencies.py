"""Dependency injection for database session."""

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """Get session factory from app state."""
    return cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)


async def get_session(
    factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncIterator[AsyncSession]:
    """Provide database session for dependency injection."""
    async with factory() as session:
        yield session
