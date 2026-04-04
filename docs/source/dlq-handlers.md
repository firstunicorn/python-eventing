# Dead letter queue (DLQ) handler guide

**API Reference:** [Universal DLQ Handler](https://python-eventing.readthedocs.io/en/latest/autoapi/messaging/infrastructure/messaging/index.html) | [Kafka DLQ Handler](https://python-eventing.readthedocs.io/en/latest/autoapi/messaging/infrastructure/messaging/kafka/index.html)

## Overview

The eventing service provides two DLQ handler implementations:

1. **Universal DLQ handler** - Broker-agnostic, works with any message broker
2. **Kafka-specific DLQ handler** - Leverages Kafka features (headers, partitions, timestamps)

## When to use each

### Universal DLQ handler (recommended)

**Use when:**
- You want broker portability (RabbitMQ, Kafka, Redis, NATS)
- You don't need Kafka-specific features
- You're building a library or reusable component

**Import:**
```python
from messaging.infrastructure.messaging.dead_letter_handler import DeadLetterHandler
from python_outbox_core import IEventPublisher, IOutboxRepository

handler = DeadLetterHandler(repository, publisher)  # Any IEventPublisher
```

### Kafka-specific DLQ handler

**Use when:**
- You need Kafka-specific features (headers, partition keys)
- You're committed to Kafka as your broker
- You need advanced debugging/monitoring metadata
- You need partition ordering guarantees in DLQ

**Kafka-specific features:**
- Custom headers (error reason, retry count, original topic)
- Partition key preservation (maintains event ordering)
- Timestamp control (preserves original event time)
- Kafka topic configuration

**Import:**
```python
from messaging.infrastructure.messaging.kafka.kafka_dead_letter_handler import KafkaDeadLetterHandler
from messaging.infrastructure.messaging.kafka_publisher import KafkaEventPublisher
from python_outbox_core import IOutboxRepository

handler = KafkaDeadLetterHandler(
    repository,
    publisher,  # Must be KafkaEventPublisher
    include_headers=True,
    preserve_partition_key=True,
)
```

## Examples

### Universal handler (any broker)

```python
from messaging.infrastructure.messaging.dead_letter_handler import DeadLetterHandler
from python_outbox_core import IEventPublisher

# Works with any broker implementation
handler = DeadLetterHandler(
    repository=outbox_repo,
    publisher=any_publisher,  # IEventPublisher interface
)

await handler.handle(event, error_message="Connection timeout")
```

**Published message:**
```json
{
  "event": {...},
  "error": "Connection timeout",
  "dlq_routed_at": "2026-04-03T10:30:00Z"
}
```

### Kafka handler (Kafka-specific)

```python
from messaging.infrastructure.messaging.kafka.kafka_dead_letter_handler import KafkaDeadLetterHandler
from messaging.infrastructure.messaging.kafka_publisher import KafkaEventPublisher

# Kafka-specific with advanced features
handler = KafkaDeadLetterHandler(
    repository=outbox_repo,
    publisher=kafka_publisher,  # KafkaEventPublisher concrete type
    include_headers=True,
    preserve_partition_key=True,
)

await handler.handle(
    event,
    error_message="Schema validation failed",
    retry_count=3,
    original_topic="UserEvents",
)
```

**Published message (with Kafka metadata):**
```json
{
  "event": {...},
  "error": "Schema validation failed",
  "dlq_routed_at": "2026-04-03T10:30:00Z",
  "retry_count": 3,
  "original_topic": "UserEvents",
  "_kafka_headers": {
    "x-dlq-reason": "Schema validation failed",
    "x-dlq-retry-count": "3",
    "x-dlq-original-event-type": "UserCreated",
    "x-dlq-original-topic": "UserEvents",
    "x-dlq-routed-at": "2026-04-03T10:30:00Z"
  }
}
```

## Testing

### Universal handler

```python
from unittest.mock import AsyncMock, Mock
from python_outbox_core import IEventPublisher, IOutboxRepository

async def test_universal_dlq():
    repository = Mock(spec=IOutboxRepository)
    publisher = AsyncMock(spec=IEventPublisher)
    
    handler = DeadLetterHandler(repository, publisher)
    await handler.handle(event, "Test error")
    
    repository.mark_failed.assert_called_once()
    publisher.publish.assert_called_once()
```

### Kafka handler

```python
from unittest.mock import AsyncMock, Mock
from messaging.infrastructure.messaging.kafka_publisher import KafkaEventPublisher

async def test_kafka_dlq_headers():
    repository = Mock()
    publisher = AsyncMock(spec=KafkaEventPublisher)
    
    handler = KafkaDeadLetterHandler(repository, publisher, include_headers=True)
    await handler.handle(event, "Test error", retry_count=3)
    
    # Verify Kafka-specific features
    call_args = publisher.publish_to_topic.call_args
    message = call_args[0][1]
    assert message["retry_count"] == 3
    assert "_kafka_headers" in message
```

## Comparison

| Feature | Universal handler | Kafka handler |
|---------|-------------------|---------------|
| **Abstraction** | IEventPublisher | KafkaEventPublisher |
| **Broker support** | Any | Kafka only |
| **Headers** | ❌ | ✅ |
| **Partition keys** | ❌ | ✅ |
| **Timestamps** | ❌ | ✅ |
| **Testing** | Easy (mock interface) | Moderate (mock concrete) |
| **Portability** | High | Low |
| **File location** | `universal_dead_letter_handler.py` | `kafka/kafka_dead_letter_handler.py` |

**Recommendation:** Start with universal DLQ handler. Switch to Kafka handler only when you need Kafka-specific features.
