"""
Unit tests for bastion.control.bridge module.

This module provides comprehensive testing for the Bridge class,
ensuring all functionality including compute and asset management
works correctly and handles edge cases properly.
"""

from __future__ import annotations

import pytest

from bastion.control.asset.local.local import LocalAsset
from bastion.control.bridge.bridge import Bridge
from bastion.control.compute.pyentrypoint.pyentrypoint import (
    PyEntrypointCompute,
)
from bastion.domain.bridge.base import BaseBridgeModel
from bastion.domain.compute.base import ComputeKind


class TestBridgeInitialization:
    """Test Bridge class initialization."""

    def test_create_bridge_minimal(self):
        """Test creating a bridge with minimal parameters."""
        bridge = Bridge(name="test_bridge")

        assert bridge.name == "test_bridge"
        assert bridge.domain.compute_domain is None
        assert bridge.domain.asset_domains == []
        assert bridge.description is None
        assert bridge.metadata == {}
        assert bridge.tags == {}

    def test_create_bridge_with_description(self):
        """Test creating bridge with description."""
        bridge = Bridge(name="test_bridge", description="Test bridge for data processing")

        assert bridge.name == "test_bridge"
        assert bridge.description == "Test bridge for data processing"

    def test_create_bridge_with_metadata(self):
        """Test creating bridge with metadata."""
        metadata = {"priority": "high", "version": "1.0"}
        bridge = Bridge(name="test_bridge", metadata=metadata)

        assert bridge.metadata == metadata

    def test_create_bridge_with_tags(self):
        """Test creating bridge with tags."""
        tags = {"env": "dev", "team": "data"}
        bridge = Bridge(name="test_bridge", tags=tags)

        assert bridge.tags == tags

    def test_create_bridge_with_compute_domain(self, compute_domain):
        """Test creating bridge with compute domain."""
        bridge = Bridge(name="test_bridge", compute_domain=compute_domain)

        assert bridge.domain.compute_domain is not None
        assert bridge.domain.compute_domain.name == "test_compute"

    def test_create_bridge_with_asset_domains(self, asset_domain_list):
        """Test creating bridge with asset domains."""
        bridge = Bridge(name="test_bridge", asset_domains=asset_domain_list)

        assert len(bridge.domain.asset_domains) == 2
        assert bridge.domain.asset_domains[0].name == "test_asset_1"
        assert bridge.domain.asset_domains[1].name == "test_asset_2"

    def test_create_bridge_with_all_parameters(self, compute_domain, asset_domain_list):
        """Test creating bridge with all parameters."""
        bridge = Bridge(
            name="test_bridge",
            compute_domain=compute_domain,
            asset_domains=asset_domain_list,
            description="Full test bridge",
            metadata={"key": "value"},
            tags={"env": "test"},
        )

        assert bridge.name == "test_bridge"
        assert bridge.domain.compute_domain is not None
        assert len(bridge.domain.asset_domains) == 2
        assert bridge.description == "Full test bridge"
        assert bridge.metadata == {"key": "value"}
        assert bridge.tags == {"env": "test"}


class TestBridgeComputeProperty:
    """Test Bridge compute property."""

    def test_compute_property_when_none(self):
        """Test compute property returns None when no compute is set."""
        bridge = Bridge(name="test_bridge")

        assert bridge.compute is None

    def test_compute_property_returns_compute(self, bridge_with_compute):
        """Test compute property returns IComputeLike instance."""
        compute = bridge_with_compute.compute

        assert compute is not None
        assert compute.name == "test_compute"
        assert compute.kind == ComputeKind.PY_ENTRYPOINT

    def test_compute_property_type(self, bridge_with_compute):
        """Test compute property returns correct type."""
        compute = bridge_with_compute.compute

        assert hasattr(compute, "domain")
        assert hasattr(compute, "name")
        assert hasattr(compute, "kind")


class TestBridgeAssetsProperty:
    """Test Bridge assets property."""

    def test_assets_property_when_empty(self):
        """Test assets property returns empty list when no assets."""
        bridge = Bridge(name="test_bridge")

        assets = bridge.assets
        assert isinstance(assets, list)
        assert len(assets) == 0

    def test_assets_property_returns_list(self, bridge_with_assets):
        """Test assets property returns list of IAssetLike instances."""
        assets = bridge_with_assets.assets

        assert isinstance(assets, list)
        assert len(assets) == 2
        assert assets[0].name == "test_asset_1"
        assert assets[1].name == "test_asset_2"

    def test_assets_property_type(self, bridge_with_assets):
        """Test assets property returns correct types."""
        assets = bridge_with_assets.assets

        for asset in assets:
            assert hasattr(asset, "domain")
            assert hasattr(asset, "name")
            assert hasattr(asset, "kind")
            assert hasattr(asset, "platform")


class TestBridgeSetCompute:
    """Test Bridge set_compute method."""

    def test_set_compute_with_compute_object(self, compute_object):
        """Test setting compute with IComputeLike object."""
        bridge = Bridge(name="test_bridge")
        bridge.set_compute(compute_object)

        assert bridge.domain.compute_domain is not None
        assert bridge.domain.compute_domain.name == "test_compute"
        assert bridge.compute.name == "test_compute"

    def test_set_compute_with_compute_domain(self, compute_domain):
        """Test setting compute with BaseComputeModel domain."""
        bridge = Bridge(name="test_bridge")
        bridge.set_compute(compute_domain)

        assert bridge.domain.compute_domain is not None
        assert bridge.domain.compute_domain.name == "test_compute"

    def test_set_compute_replaces_existing(self, bridge_with_compute, compute_object):
        """Test setting compute replaces existing compute."""
        # Create a new compute with different name
        new_compute = PyEntrypointCompute(name="new_compute", entrypoint="test.module.new_function")

        bridge_with_compute.set_compute(new_compute)

        assert bridge_with_compute.domain.compute_domain.name == "new_compute"
        assert bridge_with_compute.compute.name == "new_compute"

    def test_set_compute_with_invalid_raises_error(self):
        """Test setting compute with invalid value raises error."""
        bridge = Bridge(name="test_bridge")

        with pytest.raises((ValueError, AttributeError)):
            bridge.set_compute(None)

    def test_set_compute_updates_domain(self, compute_object):
        """Test set_compute properly updates the domain."""
        bridge = Bridge(name="test_bridge")

        assert bridge.domain.compute_domain is None

        bridge.set_compute(compute_object)

        assert bridge.domain.compute_domain is not None
        assert bridge.domain.compute_domain == compute_object.domain


class TestBridgeRemoveCompute:
    """Test Bridge remove_compute method."""

    def test_remove_compute_when_exists(self, bridge_with_compute):
        """Test removing compute when it exists."""
        assert bridge_with_compute.domain.compute_domain is not None

        bridge_with_compute.remove_compute()

        assert bridge_with_compute.domain.compute_domain is None
        assert bridge_with_compute.compute is None

    def test_remove_compute_when_none(self):
        """Test removing compute when none exists."""
        bridge = Bridge(name="test_bridge")

        assert bridge.domain.compute_domain is None

        # Should not raise error
        bridge.remove_compute()

        assert bridge.domain.compute_domain is None

    def test_remove_compute_idempotent(self, bridge_with_compute):
        """Test removing compute multiple times is safe."""
        bridge_with_compute.remove_compute()
        bridge_with_compute.remove_compute()

        assert bridge_with_compute.domain.compute_domain is None


class TestBridgeAddAsset:
    """Test Bridge add_asset method."""

    def test_add_asset_to_empty_bridge(self, asset_object):
        """Test adding asset to bridge with no assets."""
        bridge = Bridge(name="test_bridge")

        assert len(bridge.domain.asset_domains) == 0

        bridge.add_asset(asset_object)

        assert len(bridge.domain.asset_domains) == 1
        assert bridge.domain.asset_domains[0].name == "test_asset"

    def test_add_asset_with_asset_object(self, asset_object):
        """Test adding asset with IAssetLike object."""
        bridge = Bridge(name="test_bridge")
        bridge.add_asset(asset_object)

        assets = bridge.assets
        assert len(assets) == 1
        assert assets[0].name == "test_asset"

    def test_add_asset_with_asset_domain(self, asset_domain):
        """Test adding asset with BaseAssetModel domain."""
        bridge = Bridge(name="test_bridge")
        bridge.add_asset(asset_domain)

        assert len(bridge.domain.asset_domains) == 1
        assert bridge.domain.asset_domains[0].name == "test_asset"

    def test_add_multiple_assets(self, asset_object, asset_object_2):
        """Test adding multiple assets."""
        bridge = Bridge(name="test_bridge")

        bridge.add_asset(asset_object)
        bridge.add_asset(asset_object_2)

        assert len(bridge.domain.asset_domains) == 2
        assert bridge.domain.asset_domains[0].name == "test_asset"
        assert bridge.domain.asset_domains[1].name == "test_asset_2"

    def test_add_duplicate_asset_warns(self, asset_object, caplog):
        """Test adding duplicate asset logs warning."""
        bridge = Bridge(name="test_bridge")

        bridge.add_asset(asset_object)
        bridge.add_asset(asset_object)

        # Should not add duplicate
        assert len(bridge.domain.asset_domains) == 1

        # Should log warning
        assert "already exists" in caplog.text

    def test_add_asset_with_same_name_warns(self, caplog):
        """Test adding assets with same name warns."""
        bridge = Bridge(name="test_bridge")

        asset1 = LocalAsset.from_dict(
            {"name": "same_name", "kind": "parquet", "platform": "local", "path": "/path/1"}
        )

        asset2 = LocalAsset.from_dict(
            {"name": "same_name", "kind": "csv", "platform": "local", "path": "/path/2"}
        )

        bridge.add_asset(asset1)
        bridge.add_asset(asset2)

        # Should not add duplicate
        assert len(bridge.domain.asset_domains) == 1
        assert "already exists" in caplog.text

    def test_add_asset_with_invalid_raises_error(self):
        """Test adding invalid asset raises error."""
        bridge = Bridge(name="test_bridge")

        with pytest.raises((ValueError, AttributeError)):
            bridge.add_asset(None)

    def test_add_asset_to_existing_assets(self, bridge_with_assets, asset_object):
        """Test adding asset to bridge that already has assets."""
        initial_count = len(bridge_with_assets.domain.asset_domains)

        # Add a new asset with different name
        new_asset = LocalAsset.from_dict(
            {"name": "new_asset", "kind": "parquet", "platform": "local", "path": "/path/new"}
        )

        bridge_with_assets.add_asset(new_asset)

        assert len(bridge_with_assets.domain.asset_domains) == initial_count + 1


class TestBridgeRemoveAsset:
    """Test Bridge remove_asset method."""

    def test_remove_asset_when_exists(self, bridge_with_assets):
        """Test removing asset when it exists."""
        initial_count = len(bridge_with_assets.domain.asset_domains)

        # Get first asset to remove
        asset_to_remove = bridge_with_assets.assets[0]

        bridge_with_assets.remove_asset(asset_to_remove)

        assert len(bridge_with_assets.domain.asset_domains) == initial_count - 1

    def test_remove_asset_by_domain(self, bridge_with_assets):
        """Test removing asset by domain model."""
        asset_domain = bridge_with_assets.domain.asset_domains[0]
        initial_count = len(bridge_with_assets.domain.asset_domains)

        bridge_with_assets.remove_asset(asset_domain)

        assert len(bridge_with_assets.domain.asset_domains) == initial_count - 1

    def test_remove_asset_when_not_exists_warns(self, bridge_with_assets, caplog):
        """Test removing non-existent asset warns."""
        new_asset = LocalAsset.from_dict(
            {"name": "non_existent", "kind": "parquet", "platform": "local", "path": "/path/none"}
        )

        initial_count = len(bridge_with_assets.domain.asset_domains)

        bridge_with_assets.remove_asset(new_asset)

        # Count should not change
        assert len(bridge_with_assets.domain.asset_domains) == initial_count

        # Should log warning
        assert "does not exist" in caplog.text

    def test_remove_all_assets(self, bridge_with_assets):
        """Test removing all assets."""
        assets = bridge_with_assets.assets.copy()

        for asset in assets:
            bridge_with_assets.remove_asset(asset)

        assert len(bridge_with_assets.domain.asset_domains) == 0
        assert len(bridge_with_assets.assets) == 0

    def test_remove_asset_from_empty_bridge_warns(self, asset_object, caplog):
        """Test removing asset from empty bridge warns."""
        bridge = Bridge(name="test_bridge")

        bridge.remove_asset(asset_object)

        assert len(bridge.domain.asset_domains) == 0
        assert "does not exist" in caplog.text

    def test_remove_asset_with_invalid_raises_error(self, bridge_with_assets):
        """Test removing invalid asset raises error."""
        with pytest.raises((ValueError, AttributeError)):
            bridge_with_assets.remove_asset(None)

    def test_remove_specific_asset_preserves_others(self, bridge_with_assets):
        """Test removing specific asset preserves other assets."""
        assets = bridge_with_assets.assets
        asset_to_keep = assets[1]
        asset_to_remove = assets[0]

        bridge_with_assets.remove_asset(asset_to_remove)

        remaining_assets = bridge_with_assets.assets
        assert len(remaining_assets) == 1
        assert remaining_assets[0].name == asset_to_keep.name


class TestBridgeCheckAssetExists:
    """Test Bridge _check_asset_exists method."""

    def test_check_asset_exists_true(self, bridge_with_assets):
        """Test checking existing asset returns True."""
        asset = bridge_with_assets.assets[0]

        exists = bridge_with_assets._check_asset_exists(asset)

        assert exists is True

    def test_check_asset_exists_false(self, bridge_with_assets):
        """Test checking non-existent asset returns False."""
        new_asset = LocalAsset.from_dict(
            {"name": "non_existent", "kind": "parquet", "platform": "local", "path": "/path/none"}
        )

        exists = bridge_with_assets._check_asset_exists(new_asset)

        assert exists is False

    def test_check_asset_exists_empty_bridge(self, asset_object):
        """Test checking asset in empty bridge returns False."""
        bridge = Bridge(name="test_bridge")

        exists = bridge._check_asset_exists(asset_object)

        assert exists is False


class TestBridgeLoadAsset:
    """Test Bridge _load_asset method."""

    def test_load_asset_from_object(self, asset_object):
        """Test loading asset from IAssetLike object."""
        bridge = Bridge(name="test_bridge")

        loaded = bridge._load_asset(asset_object)

        assert loaded is not None
        assert loaded.name == "test_asset"

    def test_load_asset_from_domain(self, asset_domain):
        """Test loading asset from BaseAssetModel domain."""
        bridge = Bridge(name="test_bridge")

        loaded = bridge._load_asset(asset_domain)

        assert loaded is not None
        assert loaded.name == "test_asset"


class TestBridgeLoadCompute:
    """Test Bridge _load_compute method."""

    def test_load_compute_from_object(self, compute_object):
        """Test loading compute from IComputeLike object."""
        bridge = Bridge(name="test_bridge")

        loaded = bridge._load_compute(compute_object)

        assert loaded is not None
        assert loaded.name == "test_compute"

    def test_load_compute_from_domain(self, compute_domain):
        """Test loading compute from BaseComputeModel domain."""
        bridge = Bridge(name="test_bridge")

        loaded = bridge._load_compute(compute_domain)

        assert loaded is not None
        assert loaded.name == "test_compute"


class TestBridgeSerialization:
    """Test Bridge serialization and deserialization."""

    def test_bridge_from_dict_minimal(self):
        """Test creating bridge from minimal dict."""
        data = {"name": "test_bridge"}

        bridge = Bridge.from_dict(data)

        assert bridge.name == "test_bridge"
        assert bridge.domain.compute_domain is None
        assert bridge.domain.asset_domains == []

    def test_bridge_from_dict_with_all_fields(self, compute_domain, asset_domain_list):
        """Test creating bridge from complete dict."""
        data = {
            "name": "test_bridge",
            "compute_domain": compute_domain.export(),
            "asset_domains": [d.export() for d in asset_domain_list],
            "description": "Test description",
            "metadata": {"key": "value"},
            "tags": {"env": "test"},
        }

        bridge = Bridge.from_dict(data)

        assert bridge.name == "test_bridge"
        assert bridge.domain.compute_domain is not None
        assert len(bridge.domain.asset_domains) == 2
        assert bridge.description == "Test description"
        assert bridge.metadata == {"key": "value"}
        assert bridge.tags == {"env": "test"}

    def test_bridge_from_domain(self):
        """Test creating bridge from domain model."""
        domain = BaseBridgeModel(name="test_bridge")

        bridge = Bridge.from_domain(domain)

        assert bridge.name == "test_bridge"
        assert bridge.domain == domain

    def test_bridge_export(self, bridge_with_compute_and_assets):
        """Test exporting bridge to dict."""
        exported = bridge_with_compute_and_assets.export()

        assert isinstance(exported, dict)
        assert exported["name"] == "full_bridge"
        assert "compute_domain" in exported
        assert "asset_domains" in exported

    def test_bridge_describe(self, bridge_with_compute_and_assets):
        """Test describing bridge as JSON string."""
        description = bridge_with_compute_and_assets.describe()

        assert isinstance(description, str)
        assert "full_bridge" in description

    def test_roundtrip_export_from_dict(self, bridge_with_compute_and_assets):
        """Test export and from_dict roundtrip."""
        original = bridge_with_compute_and_assets

        # Export to dict
        exported = original.export()

        # Recreate from dict
        restored = Bridge.from_dict(exported)

        # Verify fields match
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.metadata == original.metadata
        assert restored.tags == original.tags
        assert len(restored.assets) == len(original.assets)


class TestBridgeEdgeCases:
    """Test Bridge edge cases and error handling."""

    def test_bridge_with_empty_asset_list(self):
        """Test creating bridge with empty asset list."""
        bridge = Bridge(name="test_bridge", asset_domains=[])

        assert bridge.domain.asset_domains == []
        assert bridge.assets == []

    def test_bridge_operations_preserve_metadata(self, compute_object):
        """Test operations preserve bridge metadata."""
        bridge = Bridge(name="test_bridge", metadata={"important": "data"}, tags={"env": "prod"})

        bridge.set_compute(compute_object)

        assert bridge.metadata == {"important": "data"}
        assert bridge.tags == {"env": "prod"}

    def test_bridge_multiple_operations(self, compute_object, asset_object, asset_object_2):
        """Test multiple operations in sequence."""
        bridge = Bridge(name="test_bridge")

        # Add compute
        bridge.set_compute(compute_object)
        assert bridge.compute is not None

        # Add assets
        bridge.add_asset(asset_object)
        bridge.add_asset(asset_object_2)
        assert len(bridge.assets) == 2

        # Remove one asset
        bridge.remove_asset(asset_object)
        assert len(bridge.assets) == 1

        # Remove compute
        bridge.remove_compute()
        assert bridge.compute is None

        # Bridge should still be valid
        assert bridge.name == "test_bridge"
        assert len(bridge.assets) == 1

    def test_bridge_name_required(self):
        """Test bridge requires name."""
        with pytest.raises((TypeError, ValueError)):
            Bridge()

    def test_bridge_attribute_delegation(self):
        """Test bridge delegates attributes to domain."""
        bridge = Bridge(name="test_bridge", description="Test description")

        # Should access domain attributes directly
        assert bridge.name == bridge.domain.name
        assert bridge.description == bridge.domain.description
        assert bridge.metadata == bridge.domain.metadata

    def test_assets_property_returns_new_list(self):
        """Test assets property returns new list each time."""
        bridge = Bridge(name="test_bridge")

        assets1 = bridge.assets
        assets2 = bridge.assets

        # Should be equal but not same object
        assert assets1 == assets2
        assert assets1 is not assets2


class TestBridgeIntegration:
    """Integration tests for Bridge with compute and assets."""

    def test_complete_bridge_workflow(self):
        """Test complete workflow of creating and managing a bridge."""
        # Create bridge
        bridge = Bridge(
            name="data_pipeline",
            description="ETL pipeline bridge",
            metadata={"version": "1.0"},
            tags={"env": "production"},
        )

        # Add compute
        compute = PyEntrypointCompute(name="etl_processor", entrypoint="pipelines.etl.process")
        bridge.set_compute(compute)

        # Add source assets
        source1 = LocalAsset.from_dict(
            {"name": "raw_data_1", "kind": "csv", "platform": "local", "path": "/data/raw1.csv"}
        )
        source2 = LocalAsset.from_dict(
            {"name": "raw_data_2", "kind": "csv", "platform": "local", "path": "/data/raw2.csv"}
        )

        bridge.add_asset(source1)
        bridge.add_asset(source2)

        # Verify state
        assert bridge.name == "data_pipeline"
        assert bridge.compute is not None
        assert len(bridge.assets) == 2

        # Export and recreate
        exported = bridge.export()
        restored = Bridge.from_dict(exported)

        assert restored.name == bridge.name
        assert restored.compute is not None
        assert len(restored.assets) == 2

    def test_bridge_state_consistency(self, compute_object, asset_object):
        """Test bridge maintains consistent state."""
        bridge = Bridge(name="test_bridge")

        # Initial state
        assert bridge.compute is None
        assert len(bridge.assets) == 0

        # Add compute
        bridge.set_compute(compute_object)
        assert bridge.compute is not None
        assert bridge.compute.domain == bridge.domain.compute_domain

        # Add asset
        bridge.add_asset(asset_object)
        assert len(bridge.assets) == 1
        assert bridge.assets[0].domain == bridge.domain.asset_domains[0]

        # Remove compute should not affect assets
        bridge.remove_compute()
        assert bridge.compute is None
        assert len(bridge.assets) == 1

        # Remove asset should not affect compute domain state
        bridge.remove_asset(asset_object)
        assert len(bridge.assets) == 0
        assert bridge.domain.compute_domain is None
