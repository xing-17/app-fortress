"""Unit tests for AssetFactory."""

from __future__ import annotations

import pytest

from bastion.control.asset.base.factory import AssetFactory
from bastion.control.asset.local.local import LocalAsset
from bastion.control.asset.oss.oss import OSSAsset
from bastion.control.asset.s3.s3 import S3Asset


class TestAssetFactory:
    """Test AssetFactory functionality."""

    def test_load_local_asset(self):
        """Test loading a local asset."""
        data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "local",
            "path": "/tmp/test.parquet",
        }

        asset = AssetFactory.load_from_dict(data)

        assert isinstance(asset, LocalAsset)
        assert asset.name == "test_asset"
        assert asset.platform == "local"

    def test_load_s3_asset(self):
        """Test loading an S3 asset."""
        data = {
            "name": "test_s3_asset",
            "kind": "parquet",
            "platform": "s3",
            "bucket": "test-bucket",
            "prefix": "test.parquet",
        }

        asset = AssetFactory.load_from_dict(data)

        assert isinstance(asset, S3Asset)
        assert asset.name == "test_s3_asset"
        assert asset.platform == "s3"

    def test_load_oss_asset(self):
        """Test loading an OSS asset."""
        data = {
            "name": "test_oss_asset",
            "kind": "parquet",
            "platform": "oss",
            "bucket": "test-bucket",
            "prefix": "test.parquet",
        }

        asset = AssetFactory.load_from_dict(data)

        assert isinstance(asset, OSSAsset)
        assert asset.name == "test_oss_asset"
        assert asset.platform == "oss"

    def test_load_missing_platform(self):
        """Test error when platform field is missing."""
        data = {
            "name": "test_asset",
            "kind": "parquet",
        }

        with pytest.raises(ValueError, match="missing required field: 'platform'"):
            AssetFactory.load_from_dict(data)

    def test_load_unregistered_platform(self):
        """Test error when platform is not registered."""
        data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "unknown_platform",
        }

        with pytest.raises(
            ValueError, match="No asset class registered for platform: 'unknown_platform'"
        ):
            AssetFactory.load_from_dict(data)

    def test_register_custom_asset(self):
        """Test registering a custom asset class."""

        # Create a mock asset class
        class CustomAsset:
            def __init__(self, name: str, platform: str):
                self.name = name
                self.platform = platform

            @classmethod
            def from_dict(cls, data: dict):
                return cls(
                    name=data["name"],
                    platform=data["platform"],
                )

        # Register the custom asset
        AssetFactory.register(platform="custom", asset_cls=CustomAsset)

        # Load an asset with the custom platform
        data = {
            "name": "custom_asset",
            "platform": "custom",
        }

        asset = AssetFactory.load_from_dict(data)

        assert isinstance(asset, CustomAsset)
        assert asset.name == "custom_asset"
        assert asset.platform == "custom"
