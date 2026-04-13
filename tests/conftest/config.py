"""Pytest hooks and Hypothesis configuration."""

import os
import shutil
import subprocess
from functools import lru_cache

import pytest
from hypothesis import HealthCheck, settings


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
        timeout=30,
        check=False,
    )
    return result.returncode == 0


def pytest_configure(config: pytest.Config) -> None:
    """Configure shared test settings once per test session."""
    _ = config
    _configure_hypothesis_profiles()
