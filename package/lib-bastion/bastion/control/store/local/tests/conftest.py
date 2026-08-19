"""
Pytest configuration and fixtures for bastion.control.store.local module tests.
"""

import pytest

from bastion.control.bridge.bridge import Bridge
from bastion.control.run.run import Run
from bastion.control.store.local.local import LocalStore


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary database path for testing."""
    db_path = tmp_path / "test_store.duckdb"
    return db_path


@pytest.fixture
def store_basic(temp_db_path):
    """Basic LocalStore instance for testing."""
    store = LocalStore(
        name="test_store",
        path=temp_db_path,
    )
    yield store
    store.close()


@pytest.fixture
def store_custom_tables(temp_db_path):
    """LocalStore instance with custom table names."""
    store = LocalStore(
        name="test_store_custom",
        path=temp_db_path,
        table_bridges="custom_bridges",
        table_runs="custom_runs",
    )
    yield store
    store.close()


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
