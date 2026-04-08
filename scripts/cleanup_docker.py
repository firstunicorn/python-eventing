"""Cleanup stale Docker containers before test runs.

This script removes all testcontainers to prevent Docker daemon overload.
Safe to run anytime - only removes containers labeled by testcontainers.

Uses two-step process: stop containers first, then remove after fully stopped.

Usage:
    python scripts/cleanup_docker.py
"""

from __future__ import annotations

import subprocess
import sys
import time

import structlog


def cleanup_testcontainers() -> int:
    """Remove all testcontainers using two-step process.
    
    Step 1: Stop all running testcontainers
    Step 2: Remove stopped testcontainers
    
    Returns:
        0 if successful, 1 if failed or Docker unavailable.
    """
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
            logger.error("Docker not available", stderr=result.stderr)
            return 1

        container_ids = [cid.strip() for cid in result.stdout.strip().split('\n') if cid.strip()]
        
        if not container_ids:
            logger.info("No testcontainers to clean up")
        else:
            logger.info("Found testcontainers to clean", count=len(container_ids))
            
            # Step 1: Stop running containers first
            subprocess.run(
                ["docker", "stop", *container_ids],
                capture_output=True,
                timeout=30,
                check=False,
            )
            logger.info("Stopped containers, waiting for full shutdown")
            time.sleep(2)  # Wait for containers to fully stop
            
            # Step 2: Remove stopped containers
            result = subprocess.run(
                ["docker", "rm", *container_ids],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            
            if result.returncode == 0:
                logger.info("Testcontainers cleanup complete", removed=len(container_ids))
            else:
                logger.warning("Some containers failed to remove", stderr=result.stderr)

        # Show remaining container count
        result = subprocess.run(
            ["docker", "ps", "-q"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode == 0:
            count = len([c for c in result.stdout.strip().split("\n") if c])
            logger.info("Container count", remaining=count)

        return 0

    except subprocess.TimeoutExpired:
        logger.error(
            "Docker cleanup timed out",
            suggestion="Restart Docker Desktop"
        )
        return 1
    except Exception as e:
        logger.error("Docker cleanup failed", error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(cleanup_testcontainers())
