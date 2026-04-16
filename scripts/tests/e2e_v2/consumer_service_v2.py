"""Consumer service v2 (separate database: consumer_db)."""

import logging
from typing import Any
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
from faststream.confluent import KafkaBroker

from messaging.infrastructure.persistence.processed_message_store.processed_message_store import (
    SqlAlchemyProcessedMessageStore,
)
from messaging.infrastructure.persistence.orm_models.processed_message_orm import ProcessedMessageRecord

logger = logging.getLogger(__name__)


class ConsumerServiceV2:
    """Consumer service with its own database (consumer_db)."""
    
    def __init__(self, database_url: str, kafka_bootstrap_servers: str) -> None:
        self.database_url = database_url
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.kafka_broker: KafkaBroker | None = None
        self.received_events: list[dict[str, Any]] = []
        
    async def start(self) -> None:
        """Start consumer service."""
        logger.info("=" * 60)
        logger.info("CONSUMER SERVICE: Starting initialization")
        logger.info("=" * 60)
        
        # Database setup (consumer_db)
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
        logger.info("Creating database tables for consumer_db")
        from messaging.infrastructure.persistence.orm_models.orm_base import Base
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Tables created: processed_messages")
        
        # Setup Kafka consumer with auto_offset_reset
        logger.info(f"Initializing Kafka broker: {self.kafka_bootstrap_servers}")
        self.kafka_broker = KafkaBroker(
            self.kafka_bootstrap_servers,
            # Consumer config passed via config parameter
            config={
                'auto.offset.reset': 'earliest',  # Read from beginning for new consumer groups
                'log_level': 3,  # Suppress info/debug logs (0=emerg to 7=debug)
            }
        )
        logger.info("✅ Kafka broker initialized")
        
        # Register subscriber with consumer group
        logger.info("Registering Kafka subscriber for topic: test.event_emitted_v2")
        
        @self.kafka_broker.subscriber(
            "test.event_emitted_v2",
            group_id="e2e-consumer-v2"  # Consumer group ID
        )
        async def handle_test_event_v2(message: dict[str, Any]) -> None:
            """Handle test event with idempotency in consumer_db."""
            logger.info("=" * 60)
            logger.info("CONSUMER: Received message from Kafka")
            logger.info(f"  Event Type: {message.get('eventType')}")
            logger.info(f"  Event ID: {message.get('event_id') or message.get('eventId')}")
            logger.info("=" * 60)
            
            # Extract event ID (match production code: event_id or eventId)
            message_id = message.get("event_id") or message.get("eventId")
            if not message_id:
                logger.warning("⚠️  No event ID found in message")
                self.received_events.append(message)
                return
            
            # Idempotency check in consumer_db using claim pattern
            logger.info("Starting idempotency check in consumer_db")
            async with self.session_factory() as session:
                store = SqlAlchemyProcessedMessageStore(session)
                
                async with session.begin():
                    logger.info(f"Checking if message {message_id} was already processed")
                    # claim() returns True if new (not processed), False if already processed
                    is_new = await store.claim(
                        consumer_name="e2e-consumer-v2",
                        event_id=str(message_id)
                    )
                    
                    if not is_new:
                        logger.info(f"⚠️  Message {message_id} already processed (idempotent skip)")
                        return
                    
                    # Process
                    logger.info("✅ Message is new, processing...")
                    self.received_events.append(message)
                    user_id = message.get('userId')  # camelCase from BaseEvent
                    logger.info(f"Processing event for userId: {user_id}")
                    
                    logger.info(f"✅ Message {message_id} claimed and processed in consumer_db.processed_messages")
                    logger.info("=" * 60)
        
        # Start broker
        logger.info("Starting Kafka broker")
        await self.kafka_broker.start()
        logger.info("✅ Kafka broker started and listening")
        
        logger.info("=" * 60)
        logger.info("CONSUMER SERVICE: Initialization complete")
        logger.info("=" * 60)
    
    def get_received_events(self) -> list[dict[str, Any]]:
        """Get received events."""
        return self.received_events
    
    async def get_processed_count(self) -> int:
        """Get processed messages count from consumer_db."""
        logger.info("Querying consumer_db.processed_messages count")
        async with self.session_factory() as session:
            result = await session.execute(
                select(func.count()).select_from(ProcessedMessageRecord)
            )
            count = result.scalar() or 0
            logger.info(f"✅ Found {count} processed messages in consumer_db")
            return count
    
    async def check_no_outbox(self) -> bool:
        """Verify consumer_db has NO outbox_events table/data."""
        async with self.session_factory() as session:
            try:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM outbox_events")
                )
                count = result.scalar()
                if count > 0:
                    logger.error(f"Found {count} rows in outbox_events in consumer_db!")
                    return False
                return True
            except Exception:
                # Table doesn't exist - that's correct!
                return True
    
    async def stop(self) -> None:
        """Stop consumer service."""
        if self.kafka_broker:
            logger.info("Closing Kafka broker connections...")
            await self.kafka_broker.close()
        if self.engine:
            await self.engine.dispose()
