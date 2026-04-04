"""Database session dependency injection.

Extracted from dependencies.py to follow the Single Responsibility Principle.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Create a database session for the request lifecycle.

    This dependency creates a new AsyncSession from the session factory
    stored in app state. The session is automatically closed after the
    request completes, even if an exception occurs.

    Usage in endpoints
    ------------------
    ```python
    @router.post("/events")
    async def create_event(
        data: EventCreateDTO,
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> EventResponseDTO:
        # Use session for transactional operations
        await business_repo.create(data, session=session)
        await outbox_repo.add_event(event, session=session)
        await session.commit()
        return response
    ```

    Parameters
    ----------
    request : Request
        The incoming FastAPI request object

    Yields
    ------
    AsyncSession
        A database session valid for the request duration

    Raises
    ------
    HTTPException
        503 if the session factory is not initialized
    """
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database session factory not initialized",
        )

    async with session_factory() as session:
        yield session


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
