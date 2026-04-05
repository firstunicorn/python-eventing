"""Health monitoring for eventing infrastructure.

This module provides health checks for eventing runtime:

**Outbox Health**
  - EventingHealthCheck : Monitor outbox staleness
  - Detects unpublished events older than threshold
  - Integrates with FastAPI health check endpoints

The health check helps detect:
- Outbox worker failures (events pile up unpublished)
- Kafka connectivity issues (events can't be published)
- Database issues (can't read outbox table)

See Also
--------
- messaging.infrastructure.outbox : Outbox repository and worker
- messaging.presentation.router : Health endpoint integration
"""

from messaging.infrastructure.health.outbox_health_check import EventingHealthCheck

__all__ = ["EventingHealthCheck"]
