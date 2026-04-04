"""SQLAlchemy declarative base for eventing persistence models.

This module provides the declarative `Base` class used by all SQLAlchemy ORM
models within the eventing service.

See also
--------
- messaging.infrastructure.persistence.outbox_orm : Uses this base
- messaging.infrastructure.persistence.processed_message_orm : Uses this base
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for ORM models."""
