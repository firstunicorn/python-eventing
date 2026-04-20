# Cross-service communication

## Overview

`messagekit` enables reliable event-driven communication between microservices following the **database-per-service** pattern. Each service maintains its own PostgreSQL database and communicates via shared Kafka infrastructure.

## Architecture principle: Database isolation

**Critical:** Services do NOT share databases. Each service has:

- Its own PostgreSQL database
- Its own `outbox_events` table (for producing events)
- Its own `processed_messages` table (for consuming events idempotently)

**Services communicate via Kafka** (shared event bus), not direct database access.

## Complete event flow

### Step-by-step example: User creation event

```
Service A (User Service)
    ├── Database: postgres-a:5432/users_db
    │   ├── users table
    │   └── outbox_events table
    └── Produces: UserCreated event

Service B (Analytics Service)  
    ├── Database: postgres-b:5432/analytics_db
    │   ├── analytics_data table
    │   └── processed_messages table
    └── Consumes: UserCreated from Kafka

Service C (Notification Service)
    ├── Database: postgres-c:5432/notifications_db
    │   ├── notifications table
    │   └── processed_messages table
    └── Consumes: UserCreated from RabbitMQ (via bridge)
```

### Detailed flow

#### 1. Service A produces event (postgres-a)

```python
# service-a/routes.py
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from messagekit.infrastructure.outbox import SqlAlchemyOutboxRepository
from messagekit.core import BaseEvent

app = FastAPI()

class UserCreated(BaseEvent):
    event_type: str = "user.created"
    aggregate_id: str
    user_id: int
    email: str

@app.post("/users")
async def create_user(
    data: dict,
    session: AsyncSession = Depends(get_session),
    outbox_repo: SqlAlchemyOutboxRepository = Depends(get_outbox_repo)
):
    async with session.begin():
        # 1. Business data goes to postgres-a
        user = User(**data)
        session.add(user)
        
        # 2. Event goes to outbox_events in postgres-a (same transaction)
        await outbox_repo.add_event(
            UserCreated(
                aggregate_id=f"user-{user.id}",
                user_id=user.id,
                email=user.email
            ),
            session=session
        )
        
        # 3. Atomic commit (both user + event in postgres-a)
        # If commit fails, neither persists
    
    return {"user_id": user.id}
```

**Result:** `users` table and `outbox_events` table in postgres-a both updated atomically.

#### 2. Kafka Connect CDC publishes to Kafka

Kafka Connect monitors `postgres-a.outbox_events` using PostgreSQL Write-Ahead Log (WAL):

```json
// Debezium CDC configuration
{
  "name": "service-a-outbox-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres-a",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "users_db",
    "database.server.name": "service-a",
    "table.include.list": "public.outbox_events",
    "transforms": "outbox",
    "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter"
  }
}
```

CDC detects new row in `outbox_events` and publishes to **Kafka topic: `user.created`**.

**Important:** CDC reads from postgres-a's outbox. Service B and C do NOT access postgres-a directly.

#### 3. Service B consumes from Kafka (postgres-b)

```python
# service-b/consumers.py
from faststream.kafka import KafkaBroker
from messagekit.infrastructure.pubsub.consumer_base import SqlAlchemyProcessedMessageStore

broker = KafkaBroker("kafka:9092")  # Docker service name

@broker.subscriber("user.created")
async def handle_user_created(message: dict):
    """
    FastStream connects to kafka:9092 (shared infrastructure).
    Docker DNS resolves 'kafka' to Kafka container IP.
    """
    async with session_factory() as session:
        # Idempotency check in postgres-b (NOT postgres-a)
        store = SqlAlchemyProcessedMessageStore(session)
        
        if not await store.was_processed(message["messageId"]):
            # Process business logic in postgres-b
            analytics_record = AnalyticsRecord(
                user_id=message["user_id"],
                email=message["email"],
                event_timestamp=message["timestamp"]
            )
            session.add(analytics_record)
            
            # Mark as processed in postgres-b's processed_messages table
            await store.mark_processed(message["messageId"])
            await session.commit()
```

**Key points:**

- Service B subscribes to **Kafka topic** (not postgres-a)
- Service B writes to **postgres-b** (its own database)
- Idempotency check uses **postgres-b's processed_messages table**
- Kafka is the communication medium, not database access

#### 4. Bridge forwards Kafka → RabbitMQ

The bridge service (part of standard architecture) runs the Kafka → RabbitMQ forwarder:

```python
# messagekit-bridge/main.py (thin wrapper service)
from fastapi import FastAPI
from messagekit.main._initialization.bridge_setup import initialize_production_bridge
from messagekit.config import settings

app = FastAPI(title="Messagekit Bridge")

@app.on_event("startup")
async def startup():
    # Initialize bridge: Kafka → RabbitMQ
    await initialize_production_bridge(
        session_factory=session_factory,  # Bridge's own postgres-bridge DB
        kafka_broker=kafka_broker,        # Connects to kafka:9092
        rabbit_broker=rabbit_broker,      # Connects to rabbitmq:5672
    )
    # Subscribes to Kafka topic "user.created"
    # Forwards to RabbitMQ exchange "events" with routing key "user-service.user.created"
```

#### 5. Service C consumes from RabbitMQ (postgres-c)

```python
# service-c/consumers.py
from faststream.rabbit import RabbitBroker
from messagekit.infrastructure.pubsub.consumer_base import SqlAlchemyProcessedMessageStore

rabbit_broker = RabbitBroker("amqp://guest:guest@rabbitmq:5672/")

@rabbit_broker.subscriber("events", routing_key="user-service.user.created")
async def handle_user_created(message: dict):
    """
    Consumes from RabbitMQ (via bridge).
    Docker DNS resolves 'rabbitmq' to RabbitMQ container IP.
    """
    async with session_factory() as session:
        # Idempotency check in postgres-c (NOT postgres-a or postgres-b)
        store = SqlAlchemyProcessedMessageStore(session)
        
        if not await store.was_processed(message["messageId"]):
            # Send notification (business logic in postgres-c)
            notification = Notification(
                user_id=message["user_id"],
                type="welcome_email",
                status="pending"
            )
            session.add(notification)
            
            # Mark as processed in postgres-c's processed_messages table
            await store.mark_processed(message["messageId"])
            await session.commit()
```

**Key points:**

- Service C subscribes to **RabbitMQ exchange** (forwarded from Kafka via bridge)
- Service C writes to **postgres-c** (its own database)
- Idempotency check uses **postgres-c's processed_messages table**

## Production deployment

### Docker Compose: Single file (all services)

For monorepo or tightly coupled services:

```yaml
version: '3.8'

networks:
  microservices-network:
    driver: bridge

services:
  # ============================================
  # SHARED INFRASTRUCTURE
  # ============================================
  
  kafka:
    image: confluentinc/cp-kafka:latest
    container_name: shared-kafka
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
    networks:
      - microservices-network

  rabbitmq:
    image: rabbitmq:3.13-management
    container_name: shared-rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
    networks:
      - microservices-network

  kafka-connect:
    image: debezium/connect:latest
    environment:
      BOOTSTRAP_SERVERS: kafka:9092
    networks:
      - microservices-network

  # ============================================
  # SERVICE A (Producer)
  # ============================================
  
  postgres-a:
    image: postgres:15
    environment:
      POSTGRES_DB: users_db
    networks:
      - microservices-network

  service-a:
    build: ./service-a
    depends_on:
      - postgres-a
      - kafka
    environment:
      # Service A config
      DATABASE_URL: "postgresql+asyncpg://postgres:postgres@postgres-a:5432/users_db"
      KAFKA_BOOTSTRAP_SERVERS: "kafka:9092"
    networks:
      - microservices-network

  # ============================================
  # BRIDGE (Kafka → RabbitMQ)
  # ============================================
  
  postgres-bridge:
    image: postgres:15
    environment:
      POSTGRES_DB: bridge_db
    networks:
      - microservices-network

  messagekit-bridge:
    build: ./messagekit-bridge
    depends_on:
      - kafka
      - rabbitmq
      - postgres-bridge
    environment:
      # Bridge config
      DATABASE_URL: "postgresql+asyncpg://postgres:postgres@postgres-bridge:5432/bridge_db"
      KAFKA_BOOTSTRAP_SERVERS: "kafka:9092"
      KAFKA_TOPIC: "user.created"
      RABBITMQ_URL: "amqp://guest:guest@rabbitmq:5672/"
      RABBITMQ_EXCHANGE: "events"
    networks:
      - microservices-network

  # ============================================
  # SERVICE B (Kafka Consumer)
  # ============================================
  
  postgres-b:
    image: postgres:15
    environment:
      POSTGRES_DB: analytics_db
    networks:
      - microservices-network

  service-b:
    build: ./service-b
    depends_on:
      - postgres-b
      - kafka
    environment:
      # Service B config
      DATABASE_URL: "postgresql+asyncpg://postgres:postgres@postgres-b:5432/analytics_db"
      KAFKA_BOOTSTRAP_SERVERS: "kafka:9092"
    networks:
      - microservices-network

  # ============================================
  # SERVICE C (RabbitMQ Consumer)
  # ============================================
  
  postgres-c:
    image: postgres:15
    environment:
      POSTGRES_DB: notifications_db
    networks:
      - microservices-network

  service-c:
    build: ./service-c
    depends_on:
      - postgres-c
      - rabbitmq
    environment:
      # Service C config
      DATABASE_URL: "postgresql+asyncpg://postgres:postgres@postgres-c:5432/notifications_db"
      RABBITMQ_URL: "amqp://guest:guest@rabbitmq:5672/"
    networks:
      - microservices-network
```

### Docker networking: Service discovery

All services on the **same Docker network** enable automatic service discovery via DNS:

- `kafka:9092` → Resolves to Kafka container IP
- `rabbitmq:5672` → Resolves to RabbitMQ container IP
- `postgres-a:5432` → Resolves to Service A's Postgres IP
- `postgres-b:5432` → Resolves to Service B's Postgres IP
- `postgres-c:5432` → Resolves to Service C's Postgres IP

**No manual IP configuration needed.** Docker DNS handles everything.

### Configuration via environment variables

Each service configures `messagekit` via environment variables (read by Pydantic Settings):

**Service A (Producer):**
```ini
# Connects to its own database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres-a:5432/users_db

# CDC will publish from this database to Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

**Service B (Kafka Consumer):**
```ini
# Connects to its own database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres-b:5432/analytics_db

# Subscribes to Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

**Service C (RabbitMQ Consumer):**
```ini
# Connects to its own database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres-c:5432/notifications_db

# Subscribes to RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

**Bridge Service:**
```ini
# Connects to its own database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres-bridge:5432/bridge_db

# Consumes from Kafka, publishes to RabbitMQ
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
KAFKA_TOPIC=user.created
RABBITMQ_EXCHANGE=events
```

## Architecture decisions

### Why Kafka AND RabbitMQ?

**Both are part of the standard architecture:**

| Broker | Primary Use | Consumers | Notes |
|--------|------------|-----------|-------|
| **Kafka** | Event backbone | Python services (FastStream) | High throughput, durable, partitioned |
| **RabbitMQ** | Routing flexibility | Any service (via bridge) | Complex routing, native AMQP, easy dead-letter exchanges |

**Pattern:** Kafka is the primary event bus. RabbitMQ provides routing flexibility for services that need AMQP or complex routing patterns.

### When to consume from Kafka vs RabbitMQ

**Consume from Kafka when:**

- Service is written in Python using FastStream
- Need high throughput (millions of events)
- Need event replay from offset
- Partitioning important for scalability

**Consume from RabbitMQ when:**

- Service uses AMQP clients (Node.js, .NET, etc.)
- Need complex routing (topic exchanges, headers exchanges)
- Legacy integration requirements
- Prefer native dead-letter exchanges

### Database isolation guarantees

**What database-per-service provides:**

✅ **Transactional boundary:** Each service's business logic + events are atomic within its own database  
✅ **Service autonomy:** Services can be developed, deployed, scaled independently  
✅ **Failure isolation:** Database failure in Service A doesn't affect Service B or C  
✅ **Schema evolution:** Each service can modify its schema without coordinating with others  

**What Kafka provides:**

✅ **Event delivery guarantee:** At-least-once delivery (CDC retries on failure)  
✅ **Event ordering:** Per-partition ordering for related events  
✅ **Event replay:** Consumers can replay from any offset  
✅ **Service decoupling:** Producers don't know about consumers  

**What idempotency stores provide:**

✅ **Exactly-once processing:** Duplicate messages are safely ignored  
✅ **Consumer isolation:** Each consumer tracks its own processed messages  
✅ **Transactional safety:** Idempotency check + business logic in same transaction  

## Troubleshooting

### Issue: Service can't connect to Kafka

**Symptoms:** `Connection refused` or `Connection timed out` errors.

**Cause:** Using wrong hostname or port.

**Solution:** Use Docker service name:

```python
# ❌ Wrong (host networking)
broker = KafkaBroker("localhost:9092")

# ✅ Correct (Docker networking)
broker = KafkaBroker("kafka:9092")
```

### Issue: Events published but not consumed

**Symptoms:** Producer succeeds, but consumer never receives messages.

**Diagnosis:**

1. Check CDC connector status:
   ```bash
   curl http://kafka-connect:8083/connectors/service-a-outbox-connector/status
   ```
   
2. Check Kafka topic has messages:
   ```bash
   docker exec shared-kafka kafka-console-consumer \
     --bootstrap-server kafka:9092 \
     --topic user.created \
     --from-beginning
   ```

3. Check consumer is subscribed:
   ```python
   # Verify topic name matches
   @broker.subscriber("user.created")  # Must match CDC topic
   ```

### Issue: Duplicate event processing

**Symptoms:** Same event processed multiple times, causing duplicate side effects.

**Cause:** Consumer not using idempotency pattern.

**Solution:** Always use `SqlAlchemyProcessedMessageStore`:

```python
async with session.begin():
    store = SqlAlchemyProcessedMessageStore(session)
    
    if not await store.was_processed(message["messageId"]):
        # Business logic
        await store.mark_processed(message["messageId"])
        # Commit both business + idempotency check
```

### Issue: Bridge not forwarding to RabbitMQ

**Symptoms:** Events appear in Kafka but not RabbitMQ.

**Diagnosis:**

1. Check bridge service logs:
   ```bash
   docker logs messagekit-bridge
   ```

2. Verify bridge environment variables:
   ```ini
   KAFKA_TOPIC=user.created  # Must match producer's topic
   RABBITMQ_EXCHANGE=events  # Must match consumer's exchange
   ```

3. Check RabbitMQ exchange exists:
   ```bash
   # RabbitMQ Management UI
   http://localhost:15672/
   # Username: guest, Password: guest
   ```

## See also

- {doc}`integration-guide` - How to integrate `messagekit` in your service
- {doc}`transactional-outbox` - Outbox pattern details
- {doc}`consumer-transactions` - Idempotent consumer pattern
- {doc}`dlq-handlers` - Dead letter queue handling
