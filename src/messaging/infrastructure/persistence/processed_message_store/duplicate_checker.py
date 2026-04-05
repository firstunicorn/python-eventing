"""Duplicate claim detection for processed messages.

Checks IntegrityError messages for database-specific duplicate key violation
indicators to determine if a claim was a genuine race condition vs. other
integrity constraint failures.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError


def is_duplicate_claim(error: IntegrityError) -> bool:
    """Check if an IntegrityError indicates a duplicate claim.

    Examines the error message for database-specific duplicate key violation
    indicators like "duplicate" or "unique" constraint violations.

    Args:
        error (IntegrityError): The SQLAlchemy IntegrityError to inspect

    Returns:
        bool: True if the error indicates a duplicate claim, False otherwise.
    """
    message = str(error.orig).lower() if error.orig is not None else str(error).lower()
    return "duplicate" in message or "unique" in message
