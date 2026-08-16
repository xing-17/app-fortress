"""Unit tests for asset base protocol."""

from __future__ import annotations

import pytest

from bastion.control.asset.base.base import IAssetLike
from bastion.control.asset.local.local import LocalAsset


class TestIAssetLikeProtocol:
    """Test IAssetLike protocol definition."""

    def test_protocol_check_with_local_asset(self):
        """Test that LocalAsset implements IAssetLike protocol."""
        asset = LocalAsset.from_dict({
            "name": "test_asset",
            "kind": "parquet",
            "platform": "local",
            "path": "/tmp/test.parquet",
        })
        
        assert isinstance(asset, IAssetLike)

    def test_protocol_required_attributes(self):
        """Test protocol required attributes are accessible."""
        asset = LocalAsset.from_dict({
            "name": "test_asset",
            "kind": "csv",
            "platform": "local",
            "path": "/tmp/test.csv",
            "description": "Test asset",
            "owner": "test_user",
            "metadata": {"key": "value"},
            "tags": {"env": "test"},
        })
        
        # Test protocol attributes
        assert asset.name == "test_asset"
        assert asset.kind == "csv"
        assert asset.platform == "local"
        assert asset.description == "Test asset"
        assert asset.owner == "test_user"
        assert asset.metadata == {"key": "value"}
        assert asset.tags == {"env": "test"}

    def test_protocol_required_methods(self):
        """Test protocol required methods exist."""
        asset = LocalAsset.from_dict({
            "name": "test_asset",
            "kind": "parquet",
            "platform": "local",
            "path": "/tmp/test.parquet",
        })
        
        # Test protocol methods
        assert hasattr(asset, "get_location_uri")
        assert hasattr(asset, "export")
        assert hasattr(asset, "describe")
        assert callable(asset.get_location_uri)
        assert callable(asset.export)
        assert callable(asset.describe)
