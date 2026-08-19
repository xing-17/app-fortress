"""
Pytest configuration and fixtures for bastion.control.bridge module tests.
"""

import pytest

from bastion.control.asset.local.local import LocalAsset, LocalAssetModel
from bastion.control.bridge.bridge import Bridge
from bastion.control.compute.pyentrypoint.pyentrypoint import (
    PyEntrypointCompute,
    PyEntrypointModel,
)
from bastion.domain.asset.base import AssetKind, AssetPlatform

# ============================================================================
# Compute Fixtures
# ============================================================================


@pytest.fixture
def compute_domain():
    """PyEntrypointModel domain for testing."""
    return PyEntrypointModel(
        name="test_compute",
        entrypoint="test.module.function",
    )


@pytest.fixture
def compute_object():
    """PyEntrypointCompute object for testing."""
    return PyEntrypointCompute(
        name="test_compute",
        entrypoint="test.module.function",
    )


# ============================================================================
# Asset Fixtures
# ============================================================================


@pytest.fixture
def asset_domain():
    """LocalAssetModel domain for testing."""
    return LocalAssetModel(
        name="test_asset",
        kind=AssetKind.PARQUET,
        platform=AssetPlatform.LOCAL,
        path="/tmp/test.parquet",
    )


@pytest.fixture
def asset_domain_list():
    """List of asset domains for testing."""
    return [
        LocalAssetModel(
            name="test_asset_1",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.LOCAL,
            path="/tmp/test1.parquet",
        ),
        LocalAssetModel(
            name="test_asset_2",
            kind=AssetKind.CSV,
            platform=AssetPlatform.LOCAL,
            path="/tmp/test2.csv",
        ),
    ]


@pytest.fixture
def asset_object():
    """LocalAsset object for testing."""
    return LocalAsset.from_dict(
        {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "local",
            "path": "/tmp/test.parquet",
        }
    )


@pytest.fixture
def asset_object_2():
    """Second LocalAsset object for testing."""
    return LocalAsset.from_dict(
        {
            "name": "test_asset_2",
            "kind": "csv",
            "platform": "local",
            "path": "/tmp/test2.csv",
        }
    )


# ============================================================================
# Bridge Fixtures
# ============================================================================


@pytest.fixture
def bridge_minimal():
    """Minimal bridge for testing."""
    return Bridge(name="test_bridge")


@pytest.fixture
def bridge_with_compute(compute_domain):
    """Bridge with compute for testing."""
    return Bridge(
        name="test_bridge",
        compute_domain=compute_domain,
    )


@pytest.fixture
def bridge_with_assets(asset_domain_list):
    """Bridge with assets for testing."""
    return Bridge(
        name="test_bridge",
        asset_domains=asset_domain_list,
    )


@pytest.fixture
def bridge_with_compute_and_assets(compute_domain, asset_domain_list):
    """Bridge with both compute and assets for testing."""
    return Bridge(
        name="full_bridge",
        compute_domain=compute_domain,
        asset_domains=asset_domain_list,
        description="Full test bridge",
        metadata={"version": "1.0", "priority": "high"},
        tags={"env": "test", "team": "data"},
    )


# ============================================================================
# Data Fixtures
# ============================================================================


@pytest.fixture
def bridge_dict_minimal():
    """Minimal bridge data dictionary for testing."""
    return {
        "name": "test_bridge",
    }


@pytest.fixture
def bridge_dict_full(compute_domain, asset_domain_list):
    """Complete bridge data dictionary for testing."""
    return {
        "name": "test_bridge",
        "compute_domain": compute_domain.export(),
        "asset_domains": [d.export() for d in asset_domain_list],
        "description": "Test bridge description",
        "metadata": {"key": "value", "priority": "high"},
        "tags": {"env": "test", "version": "1.0"},
    }
