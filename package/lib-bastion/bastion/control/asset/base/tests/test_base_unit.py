"""
Unit tests for bastion.control.asset.base module.

Coverage:
- TestIAssetLike: Protocol structure validation and implementation checks.
"""

from __future__ import annotations

from typing import Any

from bastion.control.asset.base.base import IAssetLike
from bastion.domain.asset.base import AssetKind, AssetPlatform, BaseAssetModel

# ──────────────────────────────────────────────────────────────────────────────
# Mock implementations for testing
# ──────────────────────────────────────────────────────────────────────────────


class MockAssetModel(BaseAssetModel):
    """Mock asset model for testing."""

    def export(self) -> dict[str, Any]:
        return super().export()


class MockAsset:
    """Mock asset implementing IAssetLike protocol."""

    def __init__(self):
        self.domain = MockAssetModel(
            name="test_asset",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.LOCAL,
        )

    def get_location_uri(self) -> str:
        return f"mock://{self.domain.name}"


class InvalidAsset:
    """Asset missing required protocol methods."""

    def __init__(self):
        self.domain = MockAssetModel(
            name="invalid",
            kind=AssetKind.CSV,
            platform=AssetPlatform.S3,
        )


# ──────────────────────────────────────────────────────────────────────────────
# TestIAssetLike
# ──────────────────────────────────────────────────────────────────────────────


class TestIAssetLike:
    """Test IAssetLike Protocol."""

    def test_valid_implementation_passes_isinstance_check(self):
        """Valid implementation should pass isinstance check."""
        asset = MockAsset()
        assert isinstance(asset, IAssetLike)

    def test_implementation_has_domain_attribute(self):
        """Implementation must have domain attribute."""
        asset = MockAsset()
        assert hasattr(asset, "domain")
        assert isinstance(asset.domain, BaseAssetModel)

    def test_implementation_has_get_location_uri_method(self):
        """Implementation must have get_location_uri method."""
        asset = MockAsset()
        assert hasattr(asset, "get_location_uri")
        assert callable(asset.get_location_uri)

    def test_get_location_uri_returns_string(self):
        """get_location_uri should return a string."""
        asset = MockAsset()
        uri = asset.get_location_uri()
        assert isinstance(uri, str)
        assert uri == "mock://test_asset"

    def test_invalid_implementation_fails_isinstance_check(self):
        """Implementation missing required methods should fail isinstance check."""
        invalid = InvalidAsset()
        assert not isinstance(invalid, IAssetLike)
