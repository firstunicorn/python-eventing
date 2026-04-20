# Quick Start: messagekit with Docker Kafka

Get messagekit running with Docker Kafka.

## Prerequisites

- Docker and Docker Compose
- Python 3.12+
- pip or Poetry

## Two Publishing Patterns

messagekit supports two approaches:

### 1. Direct Publishing (simpler)
Publish events directly to Kafka - no database, no CDC needed.

**Use when**: Simple event streaming, no transactional guarantees needed.

**Setup**: Skip PostgreSQL and Kafka Connect (steps 5-6 below).

**Code example**:
```python
from faststream.kafka import KafkaBroker
from messagekit.infrastructure.pubsub.kafka_publisher import KafkaEventPublisher

# Create broker and publisher
broker = KafkaBroker("localhost:9092")
await broker.connect()
publisher = KafkaEventPublisher(broker)

# Publish directly to Kafka
await publisher.publish({
    "eventType": "user.created",
    "aggregateId": "user-123",
    "data": {"email": "user@example.com"}
})
```

### 2. Transactional Outbox (robust)
Write events to database in same transaction as business logic, CDC publishes to Kafka asynchronously.

**Use when**: Need transactional guarantees (events only published if DB commit succeeds).

**Setup**: Requires PostgreSQL + Kafka Connect + CDC (steps 5-6 below).

**Code example**:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from python_outbox_core import OutboxPublisherBase
from messagekit.infrastructure.outbox.repository import SqlAlchemyOutboxRepository

# In your transaction
async with session.begin():
    # Business logic
    user = User(email="user@example.com")
    session.add(user)
    
    # Outbox event (written to DB, published by CDC)
    outbox = OutboxPublisherBase(SqlAlchemyOutboxRepository(session))
    await outbox.publish({
        "eventType": "user.created",
        "aggregateId": str(user.id),
        "data": {"email": user.email}
    })
    # Commit atomically - if this fails, event never publishes
```

## Setup

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```ini
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Only needed for transactional outbox pattern:
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/messagekit
```

### 2. Start infrastructure

**For direct publishing** (Kafka only):
```bash
docker-compose up -d kafka zookeeper
```

**For transactional outbox** (Kafka + PostgreSQL + CDC):
```bash
docker-compose up -d
```

Wait for health checks (~30 seconds):
```bash
docker-compose ps
```

### 3. Install messagekit

```bash
pip install messagekit faststream[kafka]

# For transactional outbox, also install:
pip install sqlalchemy asyncpg
```

### 4. Run your application

```bash
uvicorn main:app --reload
```

Check logs for `Application startup complete.` - no Kafka errors = success.

### 5. Configure CDC (ONLY for transactional outbox)

Skip this if using direct publishing.

For transactional outbox pattern, configure Debezium CDC connector. This tells Kafka Connect to stream changes from your PostgreSQL outbox table to Kafka.

**Where these values come from:**

| Parameter | Value | Source |
|-----------|-------|--------|
| `localhost:8083` | Kafka Connect REST API | docker-compose.yml port mapping |
| `database.hostname` | `postgres` | Docker service name from docker-compose.yml |
| `database.port` | `5432` | PostgreSQL default port |
| `database.user` | `postgres` | From docker-compose.yml `POSTGRES_USER` |
| `database.password` | `postgres` | From docker-compose.yml `POSTGRES_PASSWORD` |
| `database.dbname` | `messagekit` | From docker-compose.yml `POSTGRES_DB` |
| `database.server.name` | `myapp` | Arbitrary logical name (choose any) |
| `table.include.list` | `public.outbox_events` | Table name from messagekit ORM model |

**Create the connector:**

```bash
curl -X POST http://localhost:8083/connectors -H "Content-Type: application/json" -d '{
  "name": "outbox-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "messagekit",
    "database.server.name": "myapp",
    "table.include.list": "public.outbox_events",
    "transforms": "outbox",
    "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter"
  }
}'
```

**Note**: If you changed `POSTGRES_DB` in docker-compose.yml or `DATABASE_URL` in .env, use that database name instead of `messagekit`.

Verify: `curl http://localhost:8083/connectors/outbox-connector/status`

Expected response: `"state":"RUNNING"`

### 6. Monitor (optional)

Kafka UI: http://localhost:8090

## Pattern Comparison

| Feature | Direct Publishing | Transactional Outbox |
|---------|------------------|---------------------|
| Complexity | Low | Medium |
| Infrastructure | Kafka only | Kafka + PostgreSQL + CDC |
| Transactional guarantee | No | Yes (atomic with DB) |
| Latency | Lower (~ms) | Higher (~100ms CDC lag) |
| Use case | Simple streaming | Critical business events |

## Connection architecture

**Direct**: Your code → FastStream KafkaBroker → Kafka

**Outbox**: Your code → DB outbox table → CDC (Debezium) → Kafka

Configuration: `.env` → Settings → `create_kafka_broker()` → Auto-connect on startup

## Network modes

| Your app | Kafka | Bootstrap servers |
|----------|-------|------------------|
| Host | Docker | `localhost:9092` |
| Docker | Docker | `kafka:9092` |

## Useful commands

```bash
# Docker management
docker-compose logs -f kafka
docker-compose down

# Kafka operations
docker exec messagekit-kafka kafka-topics --list --bootstrap-server localhost:9092
docker exec messagekit-kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic events --from-beginning

# Kafka Connect (if using outbox)
curl http://localhost:8083/connectors
curl http://localhost:8083/connectors/outbox-connector/status
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Connection refused | `docker-compose up -d` |
| Wrong bootstrap servers | Use `localhost:9092` (host) or `kafka:9092` (Docker) |
| Topics not created | Auto-create enabled in docker-compose.yml |
| Connector fails (outbox) | Delete and recreate: `curl -X DELETE http://localhost:8083/connectors/outbox-connector` |

## Files

- [docker-compose.yml](../../docker-compose.yml) - Infrastructure definition
- [.env.example](../../.env.example) - Configuration template
- messagekit docs: https://messagekit.readthedocs.io/
