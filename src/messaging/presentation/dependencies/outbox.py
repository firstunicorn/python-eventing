"""Outbox repository dependency injection.

Extracted from dependencies.py to follow the Single Responsibility Principle.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from messaging.infrastructure.outbox.outbox_repository import SqlAlchemyOutboxRepository


async def get_outbox_repository(request: Request) -> SqlAlchemyOutboxRepository:
    """Retrieve the outbox repository instance from app state.

    This dependency provides access to the SqlAlchemyOutboxRepository
    that was initialized during application lifespan.

    Parameters
    ----------
    request : Request
        The incoming FastAPI request object

    Returns
    -------
    SqlAlchemyOutboxRepository
        The initialized outbox repository

    Raises
    ------
    HTTPException
        503 if the repository is not initialized
    """
    repository: SqlAlchemyOutboxRepository | None = getattr(
        request.app.state, "outbox_repository", None
    )
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Outbox repository not initialized",
        )
    return repository


OutboxRepositoryDep = Annotated[SqlAlchemyOutboxRepository, Depends(get_outbox_repository)]
