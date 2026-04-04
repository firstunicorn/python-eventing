"""FastAPI dependency injection functions for the eventing service.

This module provides typed dependencies for database sessions, outbox repository,
and health checks. These dependencies enable proper dependency injection,
testability, and type safety across the API layer.

See also
--------
- messaging.presentation.router : Where these dependencies are used
- messaging.main : Where resources are initialized in lifespan
"""

from messaging.presentation.dependencies.health_check import (
    OutboxHealthCheckDep,
    get_outbox_health_check,
)
from messaging.presentation.dependencies.outbox import (
    OutboxRepositoryDep,
    get_outbox_repository,
)
from messaging.presentation.dependencies.session import DBSessionDep, get_db_session

__all__ = [
    "DBSessionDep",
    "OutboxHealthCheckDep",
    "OutboxRepositoryDep",
    "get_db_session",
    "get_outbox_health_check",
    "get_outbox_repository",
]
