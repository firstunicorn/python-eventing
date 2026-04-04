# Python Eventing

Package-first universal eventing infrastructure shared across
microservices. Services should install the `python-eventing` distribution and
import it as `eventing`. The package owns reusable event contracts, outbox
persistence, Kafka publishing/consumption primitives, DLQ handling, health
checks, and in-process dispatch ergonomics. It does not own
gamification-specific reward rules or producer-specific business handlers.

```{toctree}
:maxdepth: 2
:caption: Contents

event-catalog
integration-guide
transactional-outbox
dlq-handlers
consumer-transactions
```

The manual pages in this guide explain the stable contracts and wiring points.
The generated API section documents the current Python implementation directly
from source.

Option 3 later: if operational needs grow, add a small Eventing ops/admin
service for replay, DLQ inspection, event catalog browsing, or observability.
That later service stays outside the hot path and does not replace the
package-first publish/consume model.
