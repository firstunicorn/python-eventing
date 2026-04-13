"""Pytest session finish cleanup."""

import subprocess
import time

import pytest
import structlog


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Cleanup ALL testcontainers on session end to prevent accumulation."""
    logger = structlog.get_logger()

    try:
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
                container_ids=container_ids[:5],
            )

            subprocess.run(
                ["docker", "stop", *container_ids],
                capture_output=True,
                timeout=30,
                check=False,
            )
            logger.debug("Stopped containers, waiting for full shutdown")
            time.sleep(2)

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
