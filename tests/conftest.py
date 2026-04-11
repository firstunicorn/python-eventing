"""Shared pytest configuration for eventing tests."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from hypothesis import HealthCheck, settings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from messaging.infrastructure.persistence.orm_models.orm_base import Base


def _configure_hypothesis_profiles() -> None:
    """Register the supported Hypothesis profiles for local and CI runs."""
    common = settings(
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    settings.register_profile("default", common)
    settings.register_profile(
        "thorough",
        settings(max_examples=1000, parent=common),
    )
    settings.register_profile(
        "stress",
        settings(max_examples=100000, parent=common),
    )
    settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "thorough"))


@lru_cache(maxsize=1)
def _docker_available() -> bool:
    """Return whether Docker is reachable from the current test environment."""
    docker_binary = shutil.which("docker")
    if docker_binary is None:
        return False
    result = subprocess.run(
        [docker_binary, "version", "--format", "{{.Server.Version}}"],
        capture_output=True,
        text=True,
        timeout=30,  # Increased from 5 to 30 seconds for slow Docker daemon
        check=False,
    )
    return result.returncode == 0


def pytest_configure(config: pytest.Config) -> None:
    """Configure shared test settings once per test session."""
    _ = config
    _configure_hypothesis_profiles()


def pytest_sessionstart(session: pytest.Session) -> None:
    """Cleanup testcontainers BEFORE tests start to ensure clean state.

    Removes any orphaned containers from previous failed/interrupted runs.
    Uses two-step process: stop first, then remove after fully stopped.

    Args:
        session: pytest session object
    """
    import time

    import structlog

    _ = session
    logger = structlog.get_logger()

    try:
        result = subprocess.run(
            # Secure: docker command with fixed args, only testcontainers-labeled containers
            ["docker", "ps", "-a", "-q", "--filter", "label=org.testcontainers=true"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            return

        container_ids = [cid.strip() for cid in result.stdout.strip().split("\n") if cid.strip()]

        if container_ids:
            logger.info(
                "Cleaning stale testcontainers before test run",
                count=len(container_ids),
            )

            # Step 1: Stop running containers first
            subprocess.run(
                ["docker", "stop", *container_ids],
                capture_output=True,
                timeout=30,
                check=False,
            )
            logger.debug("Stopped containers, waiting for full shutdown")
            time.sleep(2)  # Wait for containers to fully stop

            # Step 2: Remove stopped containers
            subprocess.run(
                ["docker", "rm", *container_ids],
                capture_output=True,
                timeout=30,
                check=False,
            )

            # Give Docker daemon time to clean up
            logger.info("Waiting for Docker daemon to stabilize after cleanup")
            time.sleep(5)
    except Exception as e:
        logger.debug("Pre-test cleanup skipped", error=str(e))


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Cleanup ALL testcontainers on session end to prevent accumulation.

    This hook runs after ALL tests complete (or are interrupted), ensuring
    orphaned containers don't accumulate and overwhelm Docker daemon.

    Uses two-step process: stop containers first, then remove after fully stopped.
    Targets ONLY containers with org.testcontainers=true label for safety.

    Args:
        session: pytest session object
        exitstatus: test session exit status (unused, required by hook signature)
    """
    import time

    import structlog

    logger = structlog.get_logger()

    try:
        # Find all testcontainers (safe - only testcontainers-labeled)
        result = subprocess.run(
            ["docker", "ps", "-a", "-q", "--filter", "label=org.testcontainers=true"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            logger.debug("Docker not available for cleanup")
            return

        container_ids = [cid.strip() for cid in result.stdout.strip().split("\n") if cid.strip()]

        if container_ids:
            logger.warning(
                "Cleaning up testcontainers",
                count=len(container_ids),
                container_ids=container_ids[:5],  # Log first 5 for debugging
            )

            # Step 1: Stop running containers first
            subprocess.run(
                ["docker", "stop", *container_ids],
                capture_output=True,
                timeout=30,
                check=False,
            )
            logger.debug("Stopped containers, waiting for full shutdown")
            time.sleep(2)  # Wait for containers to fully stop

            # Step 2: Remove stopped containers
            subprocess.run(
                ["docker", "rm", *container_ids],
                capture_output=True,
                timeout=30,
                check=False,
            )

            logger.info("Testcontainers cleanup complete", removed=len(container_ids))
    except subprocess.TimeoutExpired:
        logger.warning("Docker cleanup timed out - Docker daemon may be slow")
    except Exception as e:
        logger.debug("Testcontainers cleanup skipped", error=str(e))


@pytest.fixture(scope="session")
def docker_or_skip() -> None:
    """Skip container-based tests when Docker is not available."""
    if not _docker_available():
        pytest.skip("Docker is unavailable in this environment")


@pytest.fixture
async def sqlite_session_factory(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]]]:
    """Create a temporary SQLite-backed async session factory for integration tests."""
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'eventing.db'}"
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield engine, factory
    await engine.dispose()


@pytest.fixture
def skip_broker_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip broker connection for HTTP-only unit/integration tests.

    This fixture uses monkeypatch to set TESTING_SKIP_BROKER environment variable,
    which tells the lifespan manager to skip Kafka broker initialization.
    This is appropriate for tests that only exercise HTTP endpoints and database logic.

    For tests that need real Kafka, use async_client_with_kafka instead.

    Args:
        monkeypatch: pytest monkeypatch fixture
    """
    monkeypatch.setenv("TESTING_SKIP_BROKER", "true")


@pytest.fixture(scope="session")
def kafka_container(docker_or_skip):
    """Provide a Kafka container for integration tests using Testcontainers.

    Requires Docker to be running. Uses confluent-kafka-python compatible container.
    Session-scoped for efficiency - container is reused across tests.

    Note: Kafka startup configured with 300-second timeout.

    Args:
        docker_or_skip: docker_or_skip

    Yields:
        kafka
    """
    from testcontainers.kafka import KafkaContainer

    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")
    kafka.start(timeout=300)

    yield kafka

    kafka.stop()


@pytest.fixture(scope="session")
def rabbitmq_container(docker_or_skip):
    """Provide a RabbitMQ container for integration tests using Testcontainers.

    Requires Docker to be running.
    Session-scoped for efficiency - container is reused across tests.

    WINDOWS LIMITATION: This fixture is infrastructure-blocked on Windows due to
    Docker Desktop networking incompatibility with RabbitMQ AMQP protocol.
    Error: WinError 1225 "connection refused" or IncompatibleProtocolError.
    Works perfectly on Linux/macOS. See PRE_RELEASE_VERIFICATION.md for details.

    Args:
        docker_or_skip: docker_or_skip

    Yields:
        rabbitmq
    """
    import os
    import time

    from testcontainers.rabbitmq import RabbitMqContainer

    # Windows-specific fix: Set TC_HOST to localhost to avoid localnpipe connection issues
    # This resolves some testcontainers networking issues on Windows Docker Desktop
    # See: https://github.com/testcontainers/testcontainers-python/issues/407
    os.environ["TC_HOST"] = "localhost"

    # Set testcontainers wait timeout to 5 minutes for slow image pulls
    # This affects the @wait_container_is_ready decorator timeout
    os.environ["TESTCONTAINERS_WAIT_TIMEOUT"] = "300"

    # Use custom credentials instead of guest/guest to avoid localhost-only restriction
    # RabbitMQ's guest user is restricted to localhost connections only
    rabbitmq = RabbitMqContainer(
        "rabbitmq:3-management",
        username="testuser",
        password="testpass",  # noqa: S106 # Test credentials, not production
    )

    with rabbitmq:
        # Container's built-in wait strategy checks connection readiness
        # Additional sleep ensures broker is fully initialized and accepting connections
        # RabbitMQ can take time to fully start accepting connections after port opens
        # Increase from 10s to 30s to handle slow Windows Docker performance
        time.sleep(30)
        yield rabbitmq


@pytest.fixture
async def async_client(
    skip_broker_in_tests: None,  # Used for side effect (sets env var)
    sqlite_session_factory: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> AsyncIterator[AsyncClient]:
    """Create async HTTP client for HTTP-only tests (no external brokers).

    This fixture is suitable for testing:
    - HTTP API endpoints (health, DLQ admin, event replay)
    - Database operations
    - Business logic that doesn't require actual message brokers

    For tests requiring real Kafka/RabbitMQ, use async_client_with_kafka.

    Args:
        skip_broker_in_tests: skip_broker_in_tests
        sqlite_session_factory: sqlite_session_factory

    Yields:
        client
    """
    from messaging.main import create_app

    app = create_app()

    # Override with test database
    engine, session_factory = sqlite_session_factory
    app.state.session_factory = session_factory

    # Initialize lifespan manually for tests
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
async def async_client_with_kafka(
    kafka_container,
    rabbitmq_container,
    sqlite_session_factory: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    """Create async HTTP client with real Kafka and RabbitMQ for integration tests.

    This fixture spins up actual broker containers and configures the app to use them.
    Suitable for testing:
    - Full event flow (publish -> consume -> process)
    - Consumer group behavior, rebalancing, partition assignment
    - Kafka-to-RabbitMQ bridge
    - Circuit breaker resilience with broker failures

    Note: Slower than async_client due to container startup. Use selectively.

    Args:
        kafka_container: kafka_container
        rabbitmq_container: rabbitmq_container
        sqlite_session_factory: sqlite_session_factory
        monkeypatch: monkeypatch

    Yields:
        client
    """
    from messaging.main import create_app

    # Configure app to use test containers
    kafka_bootstrap = kafka_container.get_bootstrap_server()
    rabbitmq_url = (
        f"amqp://{rabbitmq_container.username}:{rabbitmq_container.password}"
        f"@{rabbitmq_container.get_container_host_ip()}"
        f":{rabbitmq_container.get_exposed_port(rabbitmq_container.port)}//"
    )

    from messaging.config import settings as app_settings

    # BUG FIX: setattr() bypasses Pydantic env_prefix="EVENTING_" and import-time loading.
    # setenv() fails because: (1) env_prefix requires EVENTING_* vars, (2) settings already
    # instantiated at import time, so env changes ignored. setattr() mutates the singleton directly.
    monkeypatch.setattr(app_settings, "kafka_bootstrap_servers", kafka_bootstrap)
    monkeypatch.setattr(app_settings, "rabbitmq_url", rabbitmq_url)

    app = create_app()

    # Override with test database
    engine, session_factory = sqlite_session_factory
    app.state.session_factory = session_factory

    # Initialize lifespan with real brokers
    async with app.router.lifespan_context(app) as state:
        # BUG FIX: lifespan() yields None, not a state dict. Guard prevents TypeError.
        if state:
            app.state._state.update(state)

        # CRITICAL FIX: 5s wait for Kafka consumer group rebalancing (2-3s typical).
        # BUG HISTORY: QueueEmpty in CI — broker.start() returns before consumer is polling.
        import asyncio

        await asyncio.sleep(5)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
