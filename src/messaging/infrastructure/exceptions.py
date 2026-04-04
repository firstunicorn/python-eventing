"""Custom exceptions for the eventing infrastructure.

This module defines specific exception types for different failure scenarios
in the event publishing pipeline. Using specific exceptions enables better
error handling, monitoring, and debugging.

See also
--------
- messaging.infrastructure.outbox.outbox_worker : Uses these exceptions
- messaging.infrastructure.health.outbox_health_check : Reports on these errors
"""


class EventingError(Exception):
    """Base exception for all eventing infrastructure errors."""


class PublishError(EventingError):
    """Raised when event publishing to the broker fails.

    This includes network errors, authentication failures, and broker
    rejections. Typically indicates a transient issue that may succeed
    on retry.
    """


class SerializationError(EventingError):
    """Raised when event serialization fails.

    This indicates a problem with the event payload structure or content
    that prevents it from being converted to the wire format. Usually
    requires fixing the event data before retry.
    """


class RepositoryError(EventingError):
    """Raised when outbox repository operations fail.

    This includes database connection errors, transaction failures, and
    query errors. May indicate database availability issues.
    """


class HealthCheckError(EventingError):
    """Raised when health check operations fail unexpectedly.

    This wraps errors that occur during health status determination,
    distinct from reporting unhealthy status (which is normal operation).
    """


class ConfigurationError(EventingError):
    """Raised when infrastructure is misconfigured.

    This indicates setup problems like missing configuration values,
    invalid URLs, or incompatible settings that prevent proper operation.
    """
