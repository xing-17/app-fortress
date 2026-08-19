"""
Pytest configuration and fixtures for bastion.control.hub module integration tests.
"""

import tempfile
from pathlib import Path

import pytest

from bastion.control.asset.local import LocalAsset
from bastion.control.bridge.bridge import Bridge
from bastion.control.compute.pyentrypoint import PyEntrypointCompute
from bastion.control.hub.hub import Hub
from bastion.control.store.local.local import LocalStore
from bastion.control.store.memory.memory import MemoryStore
from bastion.domain.asset.base import AssetKind, AssetPlatform


# ============================================================================
# Test Functions for PyEntrypointCompute
# ============================================================================


def sample_task_success():
    """A simple task that succeeds."""
    return "Task completed successfully"


def sample_task_with_params(input_value: str, multiplier: int = 1):
    """A task that accepts parameters."""
    result = input_value * multiplier
    return result


def sample_task_with_file_creation(output_path: str):
    """A task that creates a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test data")
    return str(path)


def sample_task_failure():
    """A task that always fails."""
    raise RuntimeError("Task failed intentionally")


# ============================================================================
# Store Fixtures
# ============================================================================


@pytest.fixture
def memory_store():
    """Basic MemoryStore instance for testing."""
    return MemoryStore(name="test_memory_store")


@pytest.fixture
def local_store(tmp_path):
    """LocalStore instance with temporary database."""
    db_path = tmp_path / "test_bastion.db"
    return LocalStore(name="test_local_store", path=str(db_path))


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for test files."""
    return tmp_path


# ============================================================================
# Asset Fixtures
# ============================================================================


@pytest.fixture
def local_asset_simple(temp_dir):
    """Simple local asset for testing."""
    asset_path = temp_dir / "data"
    asset_path.mkdir(exist_ok=True)
    return LocalAsset(
        name="test_asset",
        kind=AssetKind.PARQUET,
        platform=AssetPlatform.LOCAL,
        path=str(asset_path),
    )


@pytest.fixture
def local_asset_stock(temp_dir):
    """Local asset representing stock data."""
    asset_path = temp_dir / "stock_daily"
    asset_path.mkdir(exist_ok=True)
    return LocalAsset(
        name="stock_daily",
        kind=AssetKind.PARQUET,
        platform=AssetPlatform.LOCAL,
        path=str(asset_path),
    )


# ============================================================================
# Compute Fixtures
# ============================================================================


@pytest.fixture
def compute_success():
    """Compute that executes a successful task."""
    return PyEntrypointCompute(
        name="test_compute_success",
        entrypoint="bastion.control.hub.tests.conftest.sample_task_success",
    )


@pytest.fixture
def compute_with_params():
    """Compute that accepts parameters."""
    return PyEntrypointCompute(
        name="test_compute_params",
        entrypoint="bastion.control.hub.tests.conftest.sample_task_with_params",
    )


@pytest.fixture
def compute_failure():
    """Compute that always fails."""
    return PyEntrypointCompute(
        name="test_compute_failure",
        entrypoint="bastion.control.hub.tests.conftest.sample_task_failure",
    )


@pytest.fixture
def compute_file_creation():
    """Compute that creates a file."""
    return PyEntrypointCompute(
        name="test_compute_file",
        entrypoint="bastion.control.hub.tests.conftest.sample_task_with_file_creation",
    )


# ============================================================================
# Bridge Fixtures
# ============================================================================


@pytest.fixture
def bridge_simple(compute_success, local_asset_simple):
    """Simple bridge with compute and asset."""
    return Bridge(
        name="test_bridge_simple",
        compute_domain=compute_success.domain,
        asset_domains=[local_asset_simple.domain],
        description="Simple test bridge",
    )


@pytest.fixture
def bridge_stock_daily(compute_success, local_asset_stock):
    """Bridge representing stock daily update."""
    return Bridge(
        name="update_stock_daily",
        compute_domain=compute_success.domain,
        asset_domains=[local_asset_stock.domain],
        description="Update stock daily data",
        tags={"env": "test", "data": "stock"},
    )


@pytest.fixture
def bridge_no_compute(local_asset_simple):
    """Bridge without compute (passive check mode)."""
    return Bridge(
        name="bridge_no_compute",
        asset_domains=[local_asset_simple.domain],
        description="Bridge without compute for passive inspection",
    )


# ============================================================================
# Hub Fixtures
# ============================================================================


@pytest.fixture
def hub_memory(memory_store):
    """Hub instance with MemoryStore."""
    return Hub(store=memory_store)


@pytest.fixture
def hub_local(local_store):
    """Hub instance with LocalStore."""
    return Hub(store=local_store)


# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
def registered_hub_memory(hub_memory, bridge_simple):
    """Hub with a registered bridge (memory store)."""
    hub_memory.register(bridge_simple)
    return hub_memory


@pytest.fixture
def registered_hub_local(hub_local, bridge_simple):
    """Hub with a registered bridge (local store)."""
    hub_local.register(bridge_simple)
    return hub_local
