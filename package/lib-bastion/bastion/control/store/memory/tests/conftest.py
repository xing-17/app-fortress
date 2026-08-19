"""
Pytest configuration and fixtures for bastion.control.store.memory module tests.
"""

import pytest

from bastion.control.bridge.bridge import Bridge
from bastion.control.run.run import Run
from bastion.control.store.memory.memory import MemoryStore


@pytest.fixture
def store_basic():
    """Basic MemoryStore instance for testing."""
    return MemoryStore(name="test_store")


@pytest.fixture
def bridge_basic():
    """Basic bridge instance for testing."""
    return Bridge(
        name="test_bridge",
        description="A test bridge",
    )


@pytest.fixture
def bridge_with_metadata():
    """Bridge instance with metadata for testing."""
    return Bridge(
        name="bridge_with_meta",
        description="Bridge with metadata",
        metadata={"version": "1.0", "author": "test"},
        tags={"env": "test", "team": "data"},
    )


@pytest.fixture
def run_basic():
    """Basic run instance for testing."""
    return Run(
        bridge_name="test_bridge",
        name="test_run",
    )


@pytest.fixture
def run_with_status(run_basic):
    """Run instance with started status."""
    run_basic.start()
    return run_basic


@pytest.fixture
def multiple_bridges():
    """Multiple bridge instances for testing."""
    return [Bridge(name=f"bridge_{i}", description=f"Bridge {i}") for i in range(5)]


@pytest.fixture
def multiple_runs():
    """Multiple run instances for testing."""
    return [Run(bridge_name="test_bridge", name=f"run_{i}") for i in range(5)]
