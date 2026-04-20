# Kafka and RabbitMQ features comparison

**[Kafka Features](#kafka-features)** • **[RabbitMQ Features](#rabbitmq-features)** • **[Feature Matrix](#feature-comparison-matrix)** • **[Configuration](#configuration-examples)**

This document provides detailed technical comparison of Kafka and RabbitMQ features with code examples from this codebase.

---

## Kafka features

### 1. Consumer-side topic pattern subscription

**Consumer-side wildcard support** (not producer-side like RabbitMQ exchanges)

```python
# Kafka consumer supports regex patterns
from faststream.confluent import KafkaBroker

broker = KafkaBroker("localhost:9092")

# Subscribe to multiple topics via regex pattern
@broker.subscriber(pattern="^customer\\..*\\.validations$")
async def handle_validations(event: dict):
    # Matches: customer.us.validations, customer.eu.validations, etc.
    pass
```

**Use case:** Single consumer subscribes to dynamically created topics matching pattern

**Limitation:** Pattern matching happens at consumer subscription time, not broker routing time

**RabbitMQ advantage:** Broker-side routing (exchange + routing keys) vs Kafka's consumer-side patterns

**Kafka alternatives for content-based routing:**
- **Kafka Connect RegexRouter SMT:** Route records to topics via regex patterns
- **Kafka Streams:** Content-based routing with `KStream.branch()` or custom Processor API
- **ksqlDB:** SQL-based routing with `WHERE` clauses and regex extraction

**References:**
- Consumer patterns: https://stackoverflow.com/questions/39520222
- Kafka Connect SMT: https://docs.confluent.io/current/connect/transforms/regexrouter.html
- Kafka Streams routing: https://www.confluent.io/blog/streaming-etl-with-confluent-kafka-message-routing-and-fan-out/

### 2. Partition-based ordering

**File:** `src/messagekit/infrastructure/pubsub/kafka_publisher.py`

```python
# Kafka publisher uses partition key for ordering guarantees
key_bytes = key.encode("utf-8") if isinstance(key, str) else key
await self._broker.publish(
    message,
    topic=topic,
    key=key_bytes,  # Messages with same key go to same partition
)
```

**Use case:** Events for same aggregate (e.g., `user-123`) must be processed in order

**Guarantee:** Same partition key → same partition → FIFO order within partition

**Example:**
```python
# All user-123 events go to same partition
await publisher.publish({
    "event_type": "user.created",
    "aggregate_id": "user-123",  # ← Partition key
    "data": {...}
})

await publisher.publish({
    "event_type": "user.updated",
    "aggregate_id": "user-123",  # ← Same partition, maintains order
    "data": {...}
})
```

### 3. Consumer groups with offset tracking

**File:** `src/messagekit/config/kafka_settings.py`

```python
kafka_consumer_conf: dict[str, str] = Field(
    default_factory=lambda: {
        "group.id": "messagekit-consumers",
        "partition.assignment.strategy": "cooperative-sticky",
        "max.poll.interval.ms": "600000",
        "session.timeout.ms": "45000",
        "heartbeat.interval.ms": "15000",
    }
)
```

**Use case:** Multiple consumer instances for horizontal scaling

**Guarantee:** Each partition assigned to only one consumer in group (at-least-once delivery)

**How it works:**
```text
Topic: user.created (3 partitions)
┌─────────────────────────────────────┐
│ Partition 0 │ Partition 1 │ Partition 2 │
└──────┬───────────┬─────────────┬─────┘
       │           │             │
Consumer Group "messagekit-consumers"
┌──────▼─────┐ ┌──▼─────┐ ┌─────▼──────┐
│ Consumer 1 │ │ Consumer 2 │ │ Consumer 3 │
└────────────┘ └────────┘ └────────────┘

Each partition assigned to exactly one consumer
Load balanced automatically by Kafka coordinator
```

### 4. Durable log retention

**Use case:** Replay events from past (time travel)

**Kafka feature:** Messages persisted for retention period (default 7 days)

**Configuration:**
```properties
# Kafka broker configuration
log.retention.hours=168  # 7 days
log.retention.bytes=-1   # Unlimited size
```

**Not available in RabbitMQ:** Messages deleted once consumed/acked

**Example replay:**
```python
# Replay from 2 days ago
from datetime import datetime, timedelta

two_days_ago = datetime.now() - timedelta(days=2)
timestamp_ms = int(two_days_ago.timestamp() * 1000)

# Seek to timestamp
consumer.seek(partition, timestamp_ms)
```

### 5. CDC-based outbox publishing

**Architecture:** Uses Kafka Connect with Debezium CDC

See {doc}`debezium-cdc-architecture` for complete details.

```mermaid
graph LR
    DB[(PostgreSQL<br/>outbox_events)] -.->|CDC Watch| CDC[Kafka Connect]
    CDC -->|Publish| Kafka([Kafka Topic])
```

**Use case:** Guaranteed event publishing from database (transactional outbox pattern)

**Kafka-specific:** CDC tools designed for Kafka topics

### 6. Autoflush control

**File:** `src/messagekit/infrastructure/pubsub/kafka_publisher.py`

```python
class KafkaEventPublisher(IEventPublisher):
    def __init__(self, broker: KafkaBroker, autoflush: bool = False):
        self._autoflush = autoflush
    
    async def publish_to_topic(self, topic: str, message: dict[str, Any]):
        if self._autoflush:
            publisher = self._broker.publisher(topic, autoflush=True)
            await publisher.publish(message, key=key_bytes)
        else:
            # Buffered for batching (better performance)
            await self._broker.publish(message, topic=topic, key=key_bytes)
```

**Use case:** Trade-off between latency (autoflush=True) and throughput (autoflush=False)

**Performance impact:**
- **autoflush=False** (default): Batch messages, higher throughput (10K+ msgs/sec)
- **autoflush=True**: Immediate flush, lower latency (~5-10ms), lower throughput (~1K msgs/sec)

---

## RabbitMQ features

### 1. Topic-based routing with wildcards

**File:** `src/messagekit/infrastructure/pubsub/bridge/routing_key_builder.py`

```python
def build_routing_key(template: str, event: dict[str, str]) -> str:
    """Build routing key like 'user.created' or 'order.placed'"""
    safe_event = {k.replace(".", "_"): v for k, v in event.items()}
    return template.format(**safe_event)
```

**Use case:** Subscribe to patterns like `user.*` or `order.#` (wildcard routing)

**Wildcard patterns:**
- `*` matches one word: `user.*` → `user.created`, `user.updated`
- `#` matches zero or more: `order.#` → `order.placed`, `order.placed.confirmed`

**Example:**
```python
from faststream.rabbit import RabbitBroker, RabbitExchange, ExchangeType

broker = RabbitBroker("amqp://guest:guest@localhost/")

# Create TOPIC exchange
exchange = RabbitExchange("events", type=ExchangeType.TOPIC)

# Subscribe to all user events
@broker.subscriber(exchange, routing_key="user.*")
async def handle_user_events(event: dict):
    # Receives: user.created, user.updated, user.deleted
    pass

# Subscribe to all order events (any depth)
@broker.subscriber(exchange, routing_key="order.#")
async def handle_order_events(event: dict):
    # Receives: order.placed, order.placed.confirmed, order.shipped.confirmed
    pass
```

### 2. Exchange types (topic, fanout, direct, headers)

**File:** `src/messagekit/infrastructure/pubsub/rabbit/publisher.py`

```python
# Explicit TOPIC exchange (supports wildcard routing)
if isinstance(default_exchange, str):
    self._default_exchange = RabbitExchange(
        default_exchange, 
        type=ExchangeType.TOPIC,  # Supports routing patterns
        durable=True
    )
```

**Exchange types:**

#### TOPIC exchange
- Wildcard routing (`user.*`, `order.#`)
- Most flexible for event-driven systems

```python
# Publisher
await publisher.publish(event, routing_key="user.created")

# Consumer 1: user.*
@broker.subscriber(exchange, routing_key="user.*")

# Consumer 2: *.created
@broker.subscriber(exchange, routing_key="*.created")
```

#### FANOUT exchange
- Broadcast to all bound queues (ignores routing key)
- Use for notifications, alerts

```python
fanout = RabbitExchange("notifications", type=ExchangeType.FANOUT)

# All subscribers receive all messages
@broker.subscriber(fanout)
async def alert_service(msg: dict): pass

@broker.subscriber(fanout)
async def log_service(msg: dict): pass
```

#### DIRECT exchange
- Exact routing key match
- Use for RPC, targeted messages

```python
direct = RabbitExchange("rpc", type=ExchangeType.DIRECT)

# Only exact match receives message
await publisher.publish(msg, routing_key="user.get_profile")

@broker.subscriber(direct, routing_key="user.get_profile")
async def get_profile(msg: dict): pass
```

#### HEADERS exchange
- Route by message headers (not routing key)
- Most flexible but slowest

```python
headers = RabbitExchange("tasks", type=ExchangeType.HEADERS)

# Match headers
@broker.subscriber(
    headers,
    arguments={
        "x-match": "all",  # or "any"
        "priority": "high",
        "type": "email"
    }
)
async def high_priority_emails(msg: dict): pass
```

**Use case:** Flexible routing without changing producer code

### 3. Publisher confirms

**File:** `src/messagekit/config/rabbitmq_settings.py`

```python
rabbitmq_publisher_confirms: bool = Field(
    default=True,
    description="Enable RabbitMQ publisher confirms for reliability",
)
```

**Use case:** Synchronous acknowledgment that message reached broker/queue

**Trade-off:** Higher latency but guaranteed delivery before returning

**RabbitMQ advantage:** Publisher confirms are a core AMQP feature with flexible options (transactional, async confirms)

**Kafka equivalent:** Producer `acks=all` with idempotence (`enable.idempotence=true`)

**Reference:** https://www.rabbitmq.com/docs/confirms

**Example:**
```python
from faststream.rabbit import RabbitBroker

broker = RabbitBroker(
    "amqp://guest:guest@localhost/",
    publisher_confirms=True  # Wait for broker confirmation
)

# Publish blocks until confirmed
await broker.publish(message, routing_key="tasks")
# ↑ Guaranteed to be in broker/queue before returning
```

### 4. Dead letter exchanges (DLX)

**File:** `src/messagekit/infrastructure/pubsub/dlq_bookkeeper/__init__.py`

```python
# @broker.subscriber("rabbitmq-dlq-queue")  # RabbitMQ DLQ queue
# async def handle_rabbitmq_dlq(msg, headers):
#     await update_db_flag_for_dlq_event(msg, headers, session_factory)
```

**Use case:** Failed messages automatically routed to DLX for retry/inspection

**RabbitMQ advantage:** Native exchange-based routing (built into broker)

**Kafka equivalent:** Kafka Connect DLQ SMT, consumer error handling, Kafka Streams DLQ patterns

**Reference:** https://www.confluent.io/learn/kafka-dead-letter-queue/

**Example configuration:**
```python
from faststream.rabbit import RabbitQueue

# Primary queue with DLX
main_queue = RabbitQueue(
    "tasks",
    arguments={
        "x-dead-letter-exchange": "dlq-exchange",
        "x-dead-letter-routing-key": "failed-tasks"
    }
)

# DLQ handler
@broker.subscriber("failed-tasks-queue")
async def handle_failed_tasks(msg: dict):
    # Inspect, log, retry, or alert
    pass
```

### 5. Priority queues

**Not available in Kafka** - Kafka uses FIFO per partition only

**RabbitMQ feature:** Messages can have priority 0-255

**Example:**
```python
# Declare priority queue
priority_queue = RabbitQueue(
    "email-tasks",
    arguments={"x-max-priority": 10}
)

# Publish with priority
await broker.publish(
    {"to": "urgent@example.com", "subject": "Alert!"},
    routing_key="email-tasks",
    priority=10  # High priority (0-10 scale)
)

await broker.publish(
    {"to": "user@example.com", "subject": "Newsletter"},
    routing_key="email-tasks",
    priority=1  # Low priority
)

# Consumer processes high-priority messages first
@broker.subscriber(priority_queue)
async def send_email(msg: dict):
    pass  # Urgent emails processed before newsletters
```

### 6. Rate limiting per consumer

**File:** `src/messagekit/config/rabbitmq_settings.py`

```python
rabbitmq_rate_limit: int = Field(default=500, description="Max messages per interval")
rabbitmq_rate_interval: float = Field(default=60.0, description="Rate window seconds")
rabbitmq_rate_limiter_enabled: bool = Field(default=False)
```

**Use case:** Protect downstream service from overload (500 msgs/minute)

**Example:**
```python
# Rate limiter middleware
from messagekit.infrastructure.pubsub.rabbit_prometheus_middleware import (
    create_rabbit_rate_limiter
)

rate_limiter = create_rabbit_rate_limiter(
    max_rate=500,      # 500 messages
    time_period=60.0   # per 60 seconds
)

broker = RabbitBroker(middlewares=[rate_limiter])
```

---

## Feature comparison matrix

### Updated matrix with Debezium CDC

| Feature | Kafka (No CDC) | Kafka + Debezium CDC | RabbitMQ Direct |
|---------|----------------|----------------------|-----------------|
| **Outbox publishing** | ⚠️ Polling worker required | ✅✅✅ Real-time WAL streaming | N/A (no native outbox) |
| **Publish latency** | 5-30 seconds | <100ms | <1ms (sub-millisecond) |
| **Database load** | High (continuous queries) | Minimal (reads WAL only) | None (no outbox) |
| **ACID guarantees** | ✅ Atomic write | ✅ Atomic write | ❌ Dual-write problem |
| **Event replay** | ✅ Time-travel | ✅ Time-travel | ❌ Consumed = deleted |
| **Multiple consumers** | ✅ Fan-out | ✅ Fan-out | ⚠️ Via exchange (no replay) |
| **Priority queues** | ❌ FIFO only | ❌ FIFO only | ✅ 0-255 levels |
| **Task distribution** | ⚠️ Possible but awkward | ⚠️ Possible but awkward | ✅ Native pattern |
| **Broker-side routing** | ❌ Consumer-side regex | ❌ Consumer-side regex | ✅ Exchange + routing keys |
| **Event sourcing** | ✅ Immutable log | ✅ Immutable log | ❌ Not designed for this |
| **Operational complexity** | Low (no CDC) | High (Kafka Connect + Debezium) | Low (single service) |
| **Throughput** | 100K+ msg/sec | 100K+ msg/sec | 50-100K msg/sec |
| **Infrastructure deps** | Kafka cluster | Kafka + PostgreSQL + Kafka Connect | RabbitMQ cluster |
| **Use case** | Event streaming (no outbox) | Event streaming (with ACID) | Task queuing, notifications |

**Key insights:**
- **Debezium makes Kafka outbox practical** (vs polling worker)
- **RabbitMQ remains superior for task queues** (priority, low latency, simplicity)
- **Both complement each other** - use Kafka for events, RabbitMQ for tasks

### Detailed feature table

| Feature | Direct Kafka | Direct RabbitMQ | Notes |
|---------|-------------|-----------------|-------|
| **Ordering guarantees** | ✅ Partition-level FIFO | ⚠️ Queue-level (single consumer) | Kafka: per-partition, RabbitMQ: per-queue |
| **Consumer scaling** | ✅ Consumer groups | ⚠️ Competing consumers | Kafka: partition-based, RabbitMQ: queue-based |
| **Event replay** | ✅ Time-travel via offsets | ❌ Consumed = deleted | Kafka's key advantage for analytics |
| **Broker-side routing** | ❌ (consumer-side regex) | ✅ Exchange + routing keys | RabbitMQ: `user.*`, Kafka: subscribe patterns |
| **Content-based routing** | ✅ Via Kafka Streams/Connect SMT | ✅ Via exchanges/headers | Both support, different mechanisms |
| **Delivery confirmation** | ✅ Producer `acks=all` | ✅ Publisher confirms | Both have reliable delivery |
| **Dead letter queues** | ✅ Via Connect SMT/consumer logic | ✅ Native DLX | Both support DLQ, different implementations |
| **Message priorities** | ❌ Not supported | ✅ Priority queues | RabbitMQ-only feature |
| **Idempotency** | ✅ Producer idempotence | ⚠️ Application-level | Kafka: built-in, RabbitMQ: manual dedup |

**Key differences:**
- **Kafka strength:** Durable log, replay, high throughput, horizontal scaling
- **RabbitMQ strength:** Flexible routing, low latency, priority queues, mature AMQP ecosystem

---

## Configuration examples

### Kafka configuration

**File:** `src/messagekit/config/kafka_settings.py`

```python
from pydantic import BaseModel, Field

class KafkaSettings(BaseModel):
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers",
    )
    
    kafka_consumer_conf: dict[str, str] = Field(
        default_factory=lambda: {
            "group.id": "messagekit-consumers",
            "partition.assignment.strategy": "cooperative-sticky",
            "max.poll.interval.ms": "600000",  # 10 minutes
            "session.timeout.ms": "45000",      # 45 seconds
            "heartbeat.interval.ms": "15000",   # 15 seconds
        }
    )
    
    rate_limiter_enabled: bool = Field(default=False)
    rate_limiter_max_rate: int = Field(default=100)
    rate_limiter_time_period: float = Field(default=1.0)
```

### RabbitMQ configuration

**File:** `src/messagekit/config/rabbitmq_settings.py`

```python
from pydantic import BaseModel, Field

class RabbitMQSettings(BaseModel):
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672//",
        description="RabbitMQ connection URL (AMQP protocol)",
    )
    
    rabbitmq_exchange: str = Field(default="events")
    rabbitmq_exchange_type: str = Field(default="topic")
    rabbitmq_exchange_durable: bool = Field(default=True)
    
    rabbitmq_publisher_confirms: bool = Field(
        default=True,
        description="Enable publisher confirms for reliability",
    )
    
    rabbitmq_rate_limit: int = Field(default=500)
    rabbitmq_rate_interval: float = Field(default=60.0)
    rabbitmq_rate_limiter_enabled: bool = Field(default=False)
```

---

## See also

- {doc}`broker-selection-guide` - When to use Kafka vs RabbitMQ (industry patterns)
- {doc}`debezium-cdc-architecture` - Technical deep dive on Debezium CDC
- {doc}`cross-service-communication` - Complete architecture and deployment
- {doc}`transactional-outbox` - Outbox pattern implementation
