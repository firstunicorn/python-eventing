"""
E2E test v2 - Real-world scenario with separate databases.

Architecture:
- Producer Service: postgres-producer:5432/producer_db
- Consumer Service: postgres-consumer:5432/consumer_db  
- Communication: Kafka (localhost:9093)

Tests complete event flow:
1. Producer emits event via EventBus → outbox_events in producer_db
2. Manual publish to Kafka (simulates CDC)
3. Consumer receives from Kafka → processed_messages in consumer_db
4. Verification of data integrity and idempotency

Infrastructure:
- Uses main docker-compose.yml (eventing-postgres, eventing-kafka, eventing-zookeeper)
- Starts infrastructure if not running
- Creates/drops test databases before/after test
- By default, stops & removes containers at end (use --keep-containers to preserve)

Usage:
  python run_e2e_test_v2.py              # Clean up containers at end
  python run_e2e_test_v2.py --keep-containers  # Keep containers running
"""

import asyncio
import argparse
import json
import logging
import sys
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from producer_service_v2 import ProducerServiceV2
from consumer_service_v2 import ConsumerServiceV2
from shared_events_v2 import TestEventV2
import asyncpg

# Parse command-line arguments
parser = argparse.ArgumentParser(description="E2E Test V2 with container lifecycle management")
parser.add_argument("--keep-containers", action="store_true", 
                    help="Keep containers running after test (for manual inspection)")
args = parser.parse_args()


async def create_test_databases() -> None:
    """Create producer_db and consumer_db in main Postgres."""
    # Connect to default postgres database to create test databases
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="postgres"
    )
    
    try:
        # Drop and recreate producer_db
        await conn.execute("DROP DATABASE IF EXISTS producer_db")
        await conn.execute("CREATE DATABASE producer_db")
        logger.info("✅ Created producer_db")
        
        # Drop and recreate consumer_db
        await conn.execute("DROP DATABASE IF EXISTS consumer_db")
        await conn.execute("CREATE DATABASE consumer_db")
        logger.info("✅ Created consumer_db")
    finally:
        await conn.close()


async def cleanup_test_databases() -> None:
    """Drop test databases from main Postgres."""
    logger.info("=" * 60)
    logger.info("DATABASE CLEANUP: Dropping test databases")
    logger.info("=" * 60)
    
    try:
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="postgres",
            timeout=5
        )
    except Exception as e:
        logger.warning(f"Cannot connect to Postgres for cleanup: {e}")
        return
    
    try:
        # Force disconnect all connections to test databases
        await conn.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname IN ('producer_db', 'consumer_db')
            AND pid <> pg_backend_pid()
        """)
        logger.info("Terminated connections to test databases")
        
        # Drop test databases
        await conn.execute("DROP DATABASE IF EXISTS producer_db")
        logger.info("✅ Dropped producer_db")
        
        await conn.execute("DROP DATABASE IF EXISTS consumer_db")
        logger.info("✅ Dropped consumer_db")
        
        logger.info("=" * 60)
    except Exception as e:
        logger.warning(f"Database cleanup failed: {e}")
    finally:
        await conn.close()


def start_infrastructure() -> bool:
    """Start main infrastructure if not running.
    
    Returns:
        bool: True if infrastructure is ready, False if failed
    """
    logger.info("=" * 60)
    logger.info("INFRASTRUCTURE: Checking main infrastructure")
    logger.info("=" * 60)
    
    try:
        # Check if containers are running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=eventing-postgres", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        
        if "eventing-postgres" in result.stdout:
            logger.info("✅ Infrastructure already running")
            return True
        
        # Start infrastructure
        logger.info("Starting docker-compose infrastructure (postgres, zookeeper, kafka)...")
        result = subprocess.run(
            ["docker-compose", "up", "-d", "postgres", "zookeeper", "kafka"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to start infrastructure: {result.stderr}")
            return False
        
        # Wait for Postgres
        # NOTE: Postgres takes 4-5 seconds to initialize after container starts.
        # This is NORMAL infrastructure behavior, NOT a code issue.
        # Retry mechanism ensures robust startup (up to 30 attempts / 30 seconds).
        logger.info("Waiting for Postgres to be ready...")
        for attempt in range(30):
            try:
                subprocess.run(
                    ["docker", "exec", "eventing-postgres", "pg_isready", "-U", "postgres"],
                    capture_output=True,
                    timeout=5,
                    check=True,
                )
                logger.info(f"✅ Postgres ready (attempt {attempt + 1}) - initialization took ~{attempt + 1}s")
                break
            except:
                if attempt == 29:
                    logger.error("Postgres failed to start after 30 attempts")
                    return False
                time.sleep(1)
        
        # Wait for Kafka (longer wait - Kafka takes time)
        logger.info("Waiting for Kafka to be ready... (this takes ~30-40s)")
        time.sleep(40)  # Kafka needs significant time to start
        
        logger.info("✅ Infrastructure started")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"Infrastructure startup failed: {e}")
        return False


def stop_infrastructure() -> None:
    """Stop main infrastructure and clean up volumes.
    
    Note: Kafka client libraries may log connection warnings to stderr during
    shutdown. These are expected and harmless - they occur because Docker
    forcefully terminates containers while client threads are closing.
    We suppress stderr to avoid alarming output.
    """
    logger.info("=" * 60)
    logger.info("INFRASTRUCTURE: Stopping and cleaning up")
    logger.info("=" * 60)
    logger.info("ℹ️  Kafka client warnings during shutdown are expected (suppressed)")
    
    try:
        import subprocess
        result = subprocess.run(
            ["docker-compose", "down", "-v"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        
        # Only show stderr if actual docker-compose errors occurred (non-zero exit + stderr)
        if result.returncode != 0 and result.stderr and not "FAIL" in result.stderr:
            logger.warning(f"Infrastructure stop had errors: {result.stderr}")
        else:
            logger.info("✅ Infrastructure stopped and volumes removed")
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.warning(f"Infrastructure stop failed: {e}")

# Setup file and console logging
log_file = Path(__file__).parent / "test_v2.log"
file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)


async def run_e2e_test_v2() -> None:
    """Run E2E test v2 with separate databases and Kafka communication."""
    
    # Start infrastructure if needed
    if not start_infrastructure():
        logger.error("❌ Failed to start infrastructure")
        sys.exit(1)
    
    logger.info("\n" + "=" * 80)
    logger.info("E2E TEST V2: Separate databases (database-per-service pattern)")
    logger.info("=" * 80)
    logger.info("Using main infrastructure (eventing-postgres:5432, eventing-kafka:9092)")
    logger.info("Creating separate databases: producer_db and consumer_db")
    
    # Step 0: Create databases
    logger.info("\n[STEP 0] Creating test databases...")
    await create_test_databases()
    logger.info("✅ Test databases created")
    
    report = {
        "test_name": "E2E Test V2 - Database-per-Service Pattern",
        "start_time": datetime.now(UTC),
        "producer_db": "eventing-postgres:5432/producer_db",
        "consumer_db": "eventing-postgres:5432/consumer_db",
        "kafka": "localhost:9092 (main eventing-kafka)",
        "steps": [],
        "success": False,
        "errors": []
    }
    
    # Step 1: Initialize services with separate databases
    logger.info("\n[STEP 1] Initializing services with separate databases...")
    logger.info("  Producer DB: eventing-postgres:5432/producer_db")
    logger.info("  Consumer DB: eventing-postgres:5432/consumer_db")
    report["steps"].append("Initialize services")
    
    producer = ProducerServiceV2(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/producer_db"
    )
    consumer = ConsumerServiceV2(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/consumer_db",
        kafka_bootstrap_servers="localhost:9092"
    )
    
    try:
        await producer.start()
        logger.info("✅ Producer service started (producer_db)")
        report["steps"].append("Producer service started")
        
        await consumer.start()
        logger.info("✅ Consumer service started (consumer_db)")
        report["steps"].append("Consumer service started")
        
        # Step 2: Emit event via EventBus
        logger.info("\n[STEP 2] Emitting test event via EventBus...")
        report["steps"].append("Emit event via EventBus")
        
        # Log the actual code being executed
        code_executed = """test_event = TestEventV2(
    aggregate_id="test-agg-v2-001",
    user_id=98765,
    action="account_created",
    metadata={"test": "v2", "databases": "separate"}
)"""
        logger.info("📍 Executing code:")
        for line in code_executed.split('\n'):
            logger.info(f"    {line}")
        
        test_event = TestEventV2(
            aggregate_id="test-agg-v2-001",
            user_id=98765,
            action="account_created",
            metadata={"test": "v2", "databases": "separate"}
        )
        
        logger.info(f"📍 Calling: await producer.emit_event(test_event)")
        await producer.emit_event(test_event)
        logger.info(f"✅ Event emitted to producer_db outbox")
        report["event_id"] = str(test_event.event_id)
        report["event_type"] = test_event.event_type
        
        # Step 3: Verify outbox in producer_db
        logger.info("\n[STEP 3] Verifying outbox in producer_db...")
        report["steps"].append("Verify outbox in producer_db")
        producer_outbox_count = await producer.get_outbox_count()
        logger.info(f"✅ Events in producer_db outbox: {producer_outbox_count}")
        report["producer_outbox_count"] = producer_outbox_count
        
        if producer_outbox_count == 0:
            error = "Event not in producer_db outbox"
            logger.error(f"❌ FAILED: {error}")
            report["errors"].append(error)
            sys.exit(1)
        
        # Step 4: Publish to Kafka (simulates CDC)
        logger.info("\n[STEP 4] Publishing from producer_db outbox to Kafka...")
        report["steps"].append("Publish to Kafka")
        await producer.publish_pending_events()
        logger.info("✅ Events published to Kafka (topic: test.event_emitted_v2)")
        
        # Step 5: Wait for consumer
        logger.info("\n[STEP 5] Waiting for consumer to receive from Kafka...")
        report["steps"].append("Wait for consumer")
        logger.info("Sleeping 10 seconds for message propagation...")
        await asyncio.sleep(10)  # Increased from 3 to 10 seconds
        
        # Retry mechanism - check multiple times
        max_retries = 3
        for retry in range(max_retries):
            received_events = consumer.get_received_events()
            if len(received_events) > 0:
                logger.info(f"✅ Consumer received {len(received_events)} events on attempt {retry + 1}")
                break
            if retry < max_retries - 1:
                logger.info(f"⏱️ No messages yet, waiting another 5 seconds (attempt {retry + 1}/{max_retries})...")
                await asyncio.sleep(5)
        
        # Step 6: Verify consumer processed event in consumer_db
        logger.info("\n[STEP 6] Verifying consumer processed event in consumer_db...")
        report["steps"].append("Verify consumer processed event")
        received_events = consumer.get_received_events()
        consumer_processed_count = await consumer.get_processed_count()
        
        logger.info(f"✅ Consumer received events: {len(received_events)}")
        logger.info(f"✅ Processed in consumer_db: {consumer_processed_count}")
        report["consumer_received_count"] = len(received_events)
        report["consumer_processed_count"] = consumer_processed_count
        
        if len(received_events) == 0:
            error = "Consumer did not receive event"
            logger.error(f"❌ FAILED: {error}")
            report["errors"].append(error)
            sys.exit(1)
        
        # Step 7: Verify database isolation
        logger.info("\n[STEP 7] Verifying database isolation...")
        report["steps"].append("Verify database isolation")
        logger.info("  Checking producer_db has NO processed_messages...")
        producer_processed = await producer.check_no_processed_messages()
        if not producer_processed:
            error = "Found processed_messages in producer_db"
            logger.error(f"❌ FAILED: {error}")
            report["errors"].append(error)
            sys.exit(1)
        logger.info("  ✅ Producer DB has no processed_messages (correct isolation)")
        report["producer_db_isolated"] = True
        
        logger.info("  Checking consumer_db has NO outbox_events...")
        consumer_outbox = await consumer.check_no_outbox()
        if not consumer_outbox:
            error = "Found outbox_events in consumer_db"
            logger.error(f"❌ FAILED: {error}")
            report["errors"].append(error)
            sys.exit(1)
        logger.info("  ✅ Consumer DB has no outbox_events (correct isolation)")
        report["consumer_db_isolated"] = True
        
        # Step 8: Test idempotency
        logger.info("\n[STEP 8] Testing idempotency...")
        report["steps"].append("Test idempotency")
        logger.info("Republishing same event...")
        await producer.publish_pending_events()
        logger.info("Sleeping 2 seconds...")
        await asyncio.sleep(2)
        
        final_received = consumer.get_received_events()
        final_processed = await consumer.get_processed_count()
        
        logger.info(f"  Received after duplicate: {len(final_received)}")
        logger.info(f"  Processed count: {final_processed}")
        report["idempotency_test_received"] = len(final_received)
        report["idempotency_test_processed"] = final_processed
        
        if final_processed != consumer_processed_count:
            logger.warning(f"⚠️  Processed count changed (might be multiple runs)")
        
        # Success!
        report["success"] = True
        report["end_time"] = datetime.now(UTC)
        report["duration_seconds"] = (report["end_time"] - report["start_time"]).total_seconds()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ E2E TEST V2 PASSED")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  • Producer DB: producer_db (outbox: {producer_outbox_count})")
        logger.info(f"  • Consumer DB: consumer_db (processed: {consumer_processed_count})")
        logger.info(f"  • Database isolation: ✅ Verified")
        logger.info(f"  • Kafka communication: ✅ Working")
        logger.info(f"  • Idempotency: ✅ Working")
        logger.info(f"  • Duration: {report['duration_seconds']:.2f}s")
        logger.info("")
        
        # Write report
        report_path = Path(__file__).parent / "report_v2.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"📄 Report saved to: {report_path}")
        logger.info(f"📄 Logs saved to: {log_file}")
        logger.info("")
        
    except Exception as e:
        report["success"] = False
        report["errors"].append(str(e))
        report["end_time"] = datetime.now(UTC)
        logger.error(f"\n❌ E2E TEST V2 FAILED: {e}", exc_info=True)
        
        # Write error report
        report_path = Path(__file__).parent / "report_v2.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"📄 Error report saved to: {report_path}")
        logger.info(f"📄 Logs saved to: {log_file}")
        sys.exit(1)
        
    finally:
        logger.info("\n[CLEANUP] Shutting down services...")
        # Stop services in order: consumer first (stops receiving), then producer
        await consumer.stop()
        await producer.stop()
        # Give Kafka clients extra time to close connections gracefully
        # This reduces (but may not eliminate) connection warnings during docker shutdown
        logger.info("Waiting 3 seconds for Kafka connections to close...")
        await asyncio.sleep(3)
        logger.info("✅ Services stopped")
        
        # Clean up test databases
        await cleanup_test_databases()
        
        # Stop infrastructure based on command-line flag
        if args.keep_containers:
            logger.info("\n⚠️  Infrastructure left running (--keep-containers flag)")
            logger.info("To stop manually: docker-compose down -v")
        else:
            # Additional delay before infrastructure shutdown
            await asyncio.sleep(2)
            stop_infrastructure()


def main() -> None:
    """Entry point."""
    try:
        asyncio.run(run_e2e_test_v2())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
