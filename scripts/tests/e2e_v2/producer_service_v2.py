"""Producer service v2 (separate database: producer_db)."""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from messaging.core.contracts.bus.event_bus import EventBus
from messaging.core.contracts import build_event_bus
from messaging.infrastructure.outbox import (
    SqlAlchemyOutboxRepository,
    OutboxEventHandler,
)
from messaging.infrastructure.persistence.orm_models.outbox_orm import OutboxEventRecord
from messaging.infrastructure.pubsub.kafka_publisher import KafkaEventPublisher
from faststream.confluent import KafkaBroker
from confluent_kafka import Producer  # Direct Kafka producer

from shared_events_v2 import TestEventV2

logger = logging.getLogger(__name__)


class ProducerServiceV2:
    """Producer service with its own database (producer_db)."""
    
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.event_bus: EventBus | None = None
        self.kafka_producer: Producer | None = None  # Direct confluent_kafka Producer
        
    async def start(self) -> None:
        """Start producer service."""
        logger.info("=" * 60)
        logger.info("PRODUCER SERVICE: Starting initialization")
        logger.info("=" * 60)
        
        # Database setup (producer_db)
        logger.info(f"Creating async engine for: {self.database_url}")
        self.engine = create_async_engine(self.database_url, echo=False)
        logger.info("✅ Engine created")
        
        logger.info("Creating session factory")
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("✅ Session factory created")
        
        # Create tables
        logger.info("Creating database tables for producer_db")
        from messaging.infrastructure.persistence.orm_models.orm_base import Base
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Tables created: outbox_events")
        
        # Setup EventBus with minimal configuration
        logger.info("Initializing EventBus")
        self.event_bus = EventBus(
            backend=None,
            hooks=None,
            settings=None
        )
        logger.info("✅ EventBus initialized")
        
        # Setup Kafka - Direct confluent_kafka Producer for reliable publishing
        logger.info("Connecting to Kafka at localhost:9092")
        self.kafka_producer = Producer({
            'bootstrap.servers': "localhost:9092",
            'client.id': 'e2e-producer-v2',
            'log_level': 3  # 0=emerg, 1=alert, 2=crit, 3=err, 4=warning (suppress info/debug)
        })
        logger.info("✅ Kafka producer initialized")
        
        logger.info("=" * 60)
        logger.info("PRODUCER SERVICE: Initialization complete")
        logger.info("=" * 60)
    
    async def emit_event(self, event: TestEventV2) -> None:
        """Emit event via EventBus (writes to producer_db outbox)."""
        logger.info("=" * 60)
        logger.info("PRODUCER: Emitting event via EventBus")
        logger.info(f"  Event ID: {event.event_id}")
        logger.info(f"  Event Type: {event.event_type}")
        logger.info(f"  Aggregate ID: {event.aggregate_id}")
        logger.info(f"  User ID: {event.user_id}")
        logger.info(f"  Action: {event.action}")
        logger.info(f"  Source: {event.source}")
        logger.info("=" * 60)
        
        logger.info("Creating outbox repository with session factory")
        outbox_repo = SqlAlchemyOutboxRepository(self.session_factory)
        outbox_handler = OutboxEventHandler(outbox_repo)
        
        logger.info("Registering event handler")
        # Clear existing handlers and register new one
        self.event_bus._handlers.clear()  # Note: _handlers is private
        self.event_bus.register(TestEventV2, outbox_handler)
        
        logger.info("📍 Executing code:")
        logger.info("    async with session.begin():")
        logger.info("        await self.event_bus.dispatch(event)")
        logger.info("    # Transaction auto-commits here")
        
        logger.info("Starting database transaction")
        async with self.session_factory() as session:
            async with session.begin():
                logger.info("Dispatching event to EventBus")
                await self.event_bus.dispatch(event)
                logger.info("✅ Event dispatched to EventBus")
            
            logger.info("✅ Transaction committed")
            logger.info("✅ Event persisted to producer_db.outbox_events")
    
    async def get_outbox_count(self) -> int:
        """Get count of events in producer_db outbox."""
        logger.info("Querying producer_db.outbox_events count")
        async with self.session_factory() as session:
            result = await session.execute(
                select(func.count()).select_from(OutboxEventRecord)
            )
            count = result.scalar() or 0
            logger.info(f"✅ Found {count} events in producer_db.outbox_events")
            return count
    
    async def publish_pending_events(self) -> None:
        """Publish from producer_db outbox to Kafka."""
        logger.info("=" * 60)
        logger.info("PRODUCER: Publishing pending events from outbox to Kafka")
        logger.info("=" * 60)
        
        async with self.session_factory() as session:
            logger.info("Querying unpublished events from producer_db.outbox_events")
            result = await session.execute(
                select(OutboxEventRecord)
                .where(OutboxEventRecord.published_at == None)  # noqa: E711
            )
            events = result.scalars().all()
            logger.info(f"Found {len(events)} unpublished events")
            
            for idx, event_record in enumerate(events, 1):
                logger.info(f"Publishing event {idx}/{len(events)}")
                logger.info(f"  Event ID: {event_record.event_id}")
                logger.info(f"  Event Type: {event_record.event_type}")
                logger.info(f"  Aggregate ID: {event_record.aggregate_id}")
                
                def delivery_callback(err, msg):
                    """Callback for Kafka delivery reports."""
                    if err:
                        logger.error(f"❌ Kafka delivery FAILED: {err}")
                    else:
                        logger.info(f"✅ Kafka delivery SUCCESS: topic={msg.topic()}, partition={msg.partition()}, offset={msg.offset()}")
                
                try:
                    # Use confluent_kafka Producer directly (pattern from integration tests)
                    import json
                    topic = event_record.event_type
                    payload_json = json.dumps(event_record.payload)
                    self.kafka_producer.produce(
                        topic=topic,
                        value=payload_json.encode('utf-8'),
                        callback=delivery_callback  # Add delivery callback
                    )
                    logger.info(f"✅ Message queued for Kafka: {topic}")
                except Exception as e:
                    logger.error(f"❌ Failed to publish: {e}")
                    raise
            
            # CRITICAL: Flush to ensure messages are sent
            logger.info("Flushing Kafka producer (max 10 seconds)...")
            unflushed = self.kafka_producer.flush(timeout=10.0)
            if unflushed > 0:
                logger.error(f"❌ {unflushed} messages failed to flush")
            else:
                logger.info("✅ All messages flushed to Kafka")
        
        logger.info("=" * 60)
        logger.info("PRODUCER: All pending events published")
        logger.info("=" * 60)
    
    async def check_no_processed_messages(self) -> bool:
        """Verify producer_db has NO processed_messages table/data."""
        async with self.session_factory() as session:
            try:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM processed_messages")
                )
                count = result.scalar()
                if count > 0:
                    logger.error(f"Found {count} rows in processed_messages in producer_db!")
                    return False
                return True
            except Exception:
                # Table doesn't exist - that's correct!
                return True
    
    async def stop(self) -> None:
        """Stop producer service."""
        if self.kafka_producer:
            # Flush any remaining messages with shorter timeout
            logger.info("Flushing Kafka producer before shutdown...")
            unflushed = self.kafka_producer.flush(timeout=2.0)
            if unflushed > 0:
                logger.warning(f"⚠️  {unflushed} messages not flushed during shutdown")
            # Important: Delete producer to cleanly close connections
            del self.kafka_producer
            self.kafka_producer = None
        if self.engine:
            await self.engine.dispose()
