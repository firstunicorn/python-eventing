"""Pytest session start cleanup."""

import csv
import io
import os
import subprocess
import time

import pytest
import structlog


def cleanup_pytest_processes() -> None:
    """Kill orphaned pytest processes on Windows."""
    logger = structlog.get_logger()
    try:
        current_pid = os.getpid()
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode == 0:
            for row in csv.reader(io.StringIO(result.stdout)):
                if row and "pytest" in " ".join(row).lower():
                    try:
                        pid = int(row[1].strip('"'))
                        if pid != current_pid:
                            subprocess.run(
                                ["taskkill", "/F", "/PID", str(pid)],
                                capture_output=True,
                                timeout=5,
                                check=False,
                            )
                            logger.debug("Killed orphaned pytest process", pid=pid)
                    except (ValueError, IndexError):
                        pass
    except Exception as e:
        logger.debug("Pytest process cleanup skipped", error=str(e))


def cleanup_docker_containers() -> None:
    """Cleanup Docker testcontainers before tests."""
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
            return

        container_ids = [cid.strip() for cid in result.stdout.strip().split("\n") if cid.strip()]

        if container_ids:
            logger.info(
                "Cleaning stale testcontainers before test run",
                count=len(container_ids),
            )

            subprocess.run(
                ["docker", "stop", "-t", "1", *container_ids],
                capture_output=True,
                timeout=30,
                check=False,
            )
            logger.debug("Stopped containers, waiting for full shutdown")
            time.sleep(2)

            subprocess.run(
                ["docker", "rm", "-f", *container_ids],
                capture_output=True,
                timeout=30,
                check=False,
            )

            logger.info("Waiting for Docker daemon to stabilize after cleanup")
            time.sleep(5)
    except Exception as e:
        logger.debug("Pre-test cleanup skipped", error=str(e))


def pytest_sessionstart(session: pytest.Session) -> None:
    """Cleanup testcontainers AND pytest processes BEFORE tests start."""
    _ = session
    cleanup_pytest_processes()
    cleanup_docker_containers()
