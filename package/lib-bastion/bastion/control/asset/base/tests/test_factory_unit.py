"""Unit tests for asset base factory."""

from __future__ import annotations

import pytest

from bastion.control.asset.base.factory import AssetFactory
from bastion.control.asset.local.local import LocalAsset
from bastion.domain.asset import BaseAssetModel


class TestAssetFactory:
    """Test AssetFactory registration and loading."""

    def test_register_and_load_from_dict(self):
        """Test registering platform and loading from dict."""
        AssetFactory._registry.clear()

        @AssetFactory.register("local")
        class TestAsset:
            pass

        assert "local" in AssetFactory._registry
        assert AssetFactory._registry["local"] is TestAsset

    def test_register_duplicate_platform_raises(self):
        """Test duplicate platform registration raises ValueError."""
        AssetFactory._registry.clear()

        @AssetFactory.register("test_platform")
        class FirstAsset:
            pass

        with pytest.raises(ValueError, match="already registered"):

            @AssetFactory.register("test_platform")
            class SecondAsset:
                pass

    def test_load_from_dict(self):
        """Test loading asset from dictionary."""
        AssetFactory._registry.clear()
        AssetFactory.register("local")(LocalAsset)

        data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "local",
            "path": "/tmp/test.parquet",
        }

        asset = AssetFactory.load(data)
        assert isinstance(asset, LocalAsset)
        assert asset.name == "test_asset"
        assert asset.platform == "local"

    def test_load_from_domain_model(self):
        """Test loading asset from domain model."""
        AssetFactory._registry.clear()
        AssetFactory.register("local")(LocalAsset)

        domain = BaseAssetModel(
            name="test_asset",
            kind="parquet",
            platform="local",
            path="/tmp/test.parquet",
        )

        asset = AssetFactory.load(domain)
        assert isinstance(asset, LocalAsset)
        assert asset.name == "test_asset"

    def test_load_missing_platform_raises(self):
        """Test loading without platform field raises ValueError."""
        AssetFactory._registry.clear()

        with pytest.raises(ValueError, match="missing required field"):
            AssetFactory.load({})

    def test_load_unregistered_platform_raises(self):
        """Test loading unregistered platform raises ValueError."""
        AssetFactory._registry.clear()

        data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "nonexistent",
            "path": "/tmp/test.parquet",
        }

        with pytest.raises(ValueError, match="No asset registered"):
            AssetFactory.load(data)
