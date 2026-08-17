"""
Unit tests for BaseBridgeModel.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bastion.domain.asset.base import AssetKind, AssetPlatform, BaseAssetModel
from bastion.domain.bridge.base import BaseBridgeModel
from bastion.domain.compute.base import BaseComputeModel, ComputeKind

# ──────────────────────────────────────────────────────────────────────────────
# Test helper classes
# ──────────────────────────────────────────────────────────────────────────────


class DummyCompute(BaseComputeModel):
    """Concrete compute implementation for testing."""

    pass


class DummyAsset(BaseAssetModel):
    """Concrete asset implementation for testing."""

    def get_location_uri(self) -> str:
        """Return a dummy URI for testing."""
        return f"dummy://{self.name}"


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_compute():
    """Create a sample compute for testing."""
    return DummyCompute(
        name="test-compute",
        kind=ComputeKind.PY_ENTRYPOINT,
        tags={"env": "test"},
    )


@pytest.fixture
def sample_asset():
    """Create a sample asset for testing."""
    return DummyAsset(
        name="test-asset",
        kind=AssetKind.PARQUET,
        platform=AssetPlatform.LOCAL,
    )


@pytest.fixture
def sample_bridge(sample_compute, sample_asset):
    """Create a sample bridge for testing."""
    return BaseBridgeModel(
        name="test-bridge",
        compute_domain=sample_compute,
        asset_domains=[sample_asset],
        description="Test bridge",
        metadata={"key": "value"},
        tags={"env": "test"},
    )


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseBridgeModel - Basic Initialization
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseBridgeModelInitialization:
    """Test suite for BaseBridgeModel initialization."""

    def test_create_bridge_with_required_fields_only(self):
        """Test creating a bridge with only required fields."""
        bridge = BaseBridgeModel(name="test-bridge")

        assert bridge.name == "test-bridge"
        assert bridge.compute_domain is None
        assert bridge.asset_domains == []
        assert bridge.description is None
        assert bridge.metadata == {}
        assert bridge.tags == {}

    def test_create_bridge_with_all_fields(self, sample_compute, sample_asset):
        """Test creating a bridge with all fields."""
        bridge = BaseBridgeModel(
            name="data-bridge",
            compute_domain=sample_compute,
            asset_domains=[sample_asset],
            description="Bridge for data processing",
            metadata={"priority": "high", "version": "1.0"},
            tags={"env": "prod", "team": "data"},
        )

        assert bridge.name == "data-bridge"
        assert bridge.compute_domain == sample_compute
        assert len(bridge.asset_domains) == 1
        assert bridge.asset_domains[0] == sample_asset
        assert bridge.description == "Bridge for data processing"
        assert bridge.metadata == {"priority": "high", "version": "1.0"}
        assert bridge.tags == {"env": "prod", "team": "data"}

    def test_create_bridge_with_multiple_assets(self, sample_compute):
        """Test creating a bridge with multiple assets."""
        asset1 = DummyAsset(
            name="asset-01",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.S3,
        )
        asset2 = DummyAsset(
            name="asset-02",
            kind=AssetKind.CSV,
            platform=AssetPlatform.LOCAL,
        )

        bridge = BaseBridgeModel(
            name="multi-asset-bridge",
            compute_domain=sample_compute,
            asset_domains=[asset1, asset2],
        )

        assert len(bridge.asset_domains) == 2
        assert bridge.asset_domains[0].name == "asset-01"
        assert bridge.asset_domains[1].name == "asset-02"

    def test_create_bridge_without_compute(self, sample_asset):
        """Test creating a bridge without compute domain."""
        bridge = BaseBridgeModel(
            name="no-compute-bridge",
            asset_domains=[sample_asset],
        )

        assert bridge.name == "no-compute-bridge"
        assert bridge.compute_domain is None
        assert len(bridge.asset_domains) == 1

    def test_create_bridge_without_assets(self, sample_compute):
        """Test creating a bridge without asset domains."""
        bridge = BaseBridgeModel(
            name="no-assets-bridge",
            compute_domain=sample_compute,
        )

        assert bridge.name == "no-assets-bridge"
        assert bridge.compute_domain == sample_compute
        assert bridge.asset_domains == []

    def test_bridge_name_required(self):
        """Test that name field is required."""
        with pytest.raises(ValidationError):
            BaseBridgeModel()


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseBridgeModel - Default Values
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseBridgeModelDefaults:
    """Test suite for BaseBridgeModel default values."""

    def test_bridge_asset_domains_default(self):
        """Test that asset_domains defaults to empty list."""
        bridge = BaseBridgeModel(name="test-bridge")

        assert isinstance(bridge.asset_domains, list)
        assert len(bridge.asset_domains) == 0

    def test_bridge_metadata_default(self):
        """Test that metadata defaults to empty dict."""
        bridge = BaseBridgeModel(name="test-bridge")

        assert isinstance(bridge.metadata, dict)
        assert len(bridge.metadata) == 0

    def test_bridge_tags_default(self):
        """Test that tags defaults to empty dict."""
        bridge = BaseBridgeModel(name="test-bridge")

        assert isinstance(bridge.tags, dict)
        assert len(bridge.tags) == 0

    def test_bridge_compute_domain_default(self):
        """Test that compute_domain defaults to None."""
        bridge = BaseBridgeModel(name="test-bridge")

        assert bridge.compute_domain is None

    def test_bridge_description_default(self):
        """Test that description defaults to None."""
        bridge = BaseBridgeModel(name="test-bridge")

        assert bridge.description is None


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseBridgeModel - Export
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseBridgeModelExport:
    """Test suite for BaseBridgeModel export functionality."""

    def test_export_bridge_minimal(self):
        """Test exporting minimal bridge to dictionary."""
        bridge = BaseBridgeModel(name="minimal-bridge")
        exported = bridge.export()

        assert exported["name"] == "minimal-bridge"
        assert exported["compute_domain"] is None
        assert exported["asset_domains"] == []
        assert exported["description"] is None
        assert exported["metadata"] == {}
        assert exported["tags"] == {}

    def test_export_bridge_with_nested_domains(self, sample_compute, sample_asset):
        """Test exporting bridge with nested domain models."""
        bridge = BaseBridgeModel(
            name="export-bridge",
            compute_domain=sample_compute,
            asset_domains=[sample_asset],
            description="Test export",
            metadata={"key": "value"},
            tags={"env": "test"},
        )

        exported = bridge.export()

        assert exported["name"] == "export-bridge"
        assert isinstance(exported["compute_domain"], dict)
        assert exported["compute_domain"]["name"] == "test-compute"
        assert exported["compute_domain"]["kind"] == "py_entrypoint"
        assert isinstance(exported["asset_domains"], list)
        assert len(exported["asset_domains"]) == 1
        assert exported["asset_domains"][0]["name"] == "test-asset"
        assert exported["description"] == "Test export"
        assert exported["metadata"] == {"key": "value"}
        assert exported["tags"] == {"env": "test"}

    def test_export_maintains_none_values(self):
        """Test that export preserves None values for optional fields."""
        bridge = BaseBridgeModel(name="minimal-bridge")
        exported = bridge.export()

        assert exported["compute_domain"] is None
        assert exported["description"] is None
        assert "compute_domain" in exported
        assert "description" in exported


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseBridgeModel - from_any
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseBridgeModelFromAny:
    """Test suite for BaseBridgeModel from_any functionality."""

    def test_from_any_with_dict_minimal(self):
        """Test from_any creates model from minimal dictionary."""
        data = {
            "name": "test-bridge",
        }
        bridge = BaseBridgeModel.from_any(data)

        assert bridge.name == "test-bridge"
        assert bridge.compute_domain is None
        assert bridge.asset_domains == []

    def test_from_any_with_dict_nested_domains(self):
        """Test from_any creates model from dictionary with nested domain dicts."""
        data = {
            "name": "test-bridge",
            "compute_domain": {
                "name": "compute-01",
                "kind": "py_entrypoint",
                "tags": {"env": "test"},
            },
            "asset_domains": [
                {
                    "name": "asset-01",
                    "kind": "parquet",
                    "platform": "s3",
                }
            ],
            "description": "Test bridge",
            "metadata": {"key": "value"},
            "tags": {"env": "test"},
        }
        bridge = BaseBridgeModel.from_any(data)

        assert bridge.name == "test-bridge"
        assert bridge.compute_domain is not None
        assert bridge.compute_domain.name == "compute-01"
        assert bridge.compute_domain.kind == ComputeKind.PY_ENTRYPOINT
        assert len(bridge.asset_domains) == 1
        assert bridge.asset_domains[0].name == "asset-01"
        assert bridge.asset_domains[0].kind == AssetKind.PARQUET
        assert bridge.description == "Test bridge"

    def test_from_any_with_model_instance(self, sample_bridge):
        """Test from_any returns same instance when given model."""
        result = BaseBridgeModel.from_any(sample_bridge)
        assert result is sample_bridge

    def test_from_any_with_none_compute(self):
        """Test from_any handles None compute_domain correctly."""
        data = {
            "name": "test-bridge",
            "compute_domain": None,
        }
        bridge = BaseBridgeModel.from_any(data)

        assert bridge.compute_domain is None

    def test_from_any_with_empty_assets(self):
        """Test from_any handles empty asset_domains correctly."""
        data = {
            "name": "test-bridge",
            "asset_domains": [],
        }
        bridge = BaseBridgeModel.from_any(data)

        assert bridge.asset_domains == []


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseBridgeModel - Roundtrip
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseBridgeModelRoundtrip:
    """Test suite for BaseBridgeModel roundtrip conversion."""

    def test_roundtrip_minimal_bridge(self):
        """Test export and from_any roundtrip with minimal bridge."""
        original = BaseBridgeModel(name="roundtrip-bridge")

        # Export to dict
        exported = original.export()

        # Recreate from dict
        restored = BaseBridgeModel.from_any(exported)

        # Verify all fields match
        assert restored.name == original.name
        assert restored.compute_domain == original.compute_domain
        assert restored.asset_domains == original.asset_domains
        assert restored.description == original.description
        assert restored.metadata == original.metadata
        assert restored.tags == original.tags

    def test_roundtrip_with_compute_and_assets(self, sample_compute):
        """Test export and from_any roundtrip with nested domains."""
        asset1 = DummyAsset(
            name="asset-01",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.S3,
        )
        asset2 = DummyAsset(
            name="asset-02",
            kind=AssetKind.CSV,
            platform=AssetPlatform.LOCAL,
        )

        original = BaseBridgeModel(
            name="roundtrip-bridge",
            compute_domain=sample_compute,
            asset_domains=[asset1, asset2],
            description="Roundtrip test",
            metadata={"priority": "high", "count": 42},
            tags={"env": "prod", "team": "data"},
        )

        # Export to dict
        exported = original.export()

        # Recreate from dict
        restored = BaseBridgeModel.from_any(exported)

        # Verify all fields match
        assert restored.name == original.name
        assert restored.compute_domain.name == original.compute_domain.name
        assert restored.compute_domain.kind == original.compute_domain.kind
        assert len(restored.asset_domains) == len(original.asset_domains)
        assert restored.asset_domains[0].name == original.asset_domains[0].name
        assert restored.asset_domains[1].name == original.asset_domains[1].name
        assert restored.description == original.description
        assert restored.metadata == original.metadata
        assert restored.tags == original.tags

    def test_roundtrip_with_none_compute(self, sample_asset):
        """Test roundtrip with None compute_domain."""
        original = BaseBridgeModel(
            name="no-compute-bridge",
            compute_domain=None,
            asset_domains=[sample_asset],
        )

        exported = original.export()
        restored = BaseBridgeModel.from_any(exported)

        assert restored.compute_domain is None
        assert len(restored.asset_domains) == 1
        assert restored.asset_domains[0].name == original.asset_domains[0].name

    def test_roundtrip_with_empty_assets(self, sample_compute):
        """Test roundtrip with empty asset_domains."""
        original = BaseBridgeModel(
            name="no-assets-bridge",
            compute_domain=sample_compute,
            asset_domains=[],
        )

        exported = original.export()
        restored = BaseBridgeModel.from_any(exported)

        assert restored.compute_domain.name == original.compute_domain.name
        assert restored.asset_domains == []

    def test_roundtrip_preserves_nested_metadata(self, sample_compute, sample_asset):
        """Test roundtrip preserves complex metadata structures."""
        original = BaseBridgeModel(
            name="complex-bridge",
            compute_domain=sample_compute,
            asset_domains=[sample_asset],
            metadata={
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "bool": True,
                "null": None,
            },
        )

        exported = original.export()
        restored = BaseBridgeModel.from_any(exported)

        assert restored.metadata == original.metadata
        assert restored.metadata["nested"]["key"] == "value"
        assert restored.metadata["list"] == [1, 2, 3]


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseBridgeModel - Edge Cases
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseBridgeModelEdgeCases:
    """Test suite for BaseBridgeModel edge cases."""

    def test_bridge_with_special_characters_in_name(self):
        """Test bridge name with special characters."""
        bridge = BaseBridgeModel(name="bridge-with_special.chars@123")
        assert bridge.name == "bridge-with_special.chars@123"

    def test_bridge_with_unicode_in_description(self):
        """Test bridge with unicode characters in description."""
        bridge = BaseBridgeModel(
            name="unicode-bridge",
            description="桥接测试 🌉 Тест",
        )
        assert "桥接测试" in bridge.description
        assert "🌉" in bridge.description

    def test_bridge_with_large_metadata(self):
        """Test bridge with large metadata dictionary."""
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(100)}
        bridge = BaseBridgeModel(
            name="large-metadata-bridge",
            metadata=large_metadata,
        )
        assert len(bridge.metadata) == 100
        assert bridge.metadata["key_50"] == "value_50"

    def test_bridge_with_empty_string_description(self):
        """Test bridge with empty string description."""
        bridge = BaseBridgeModel(
            name="empty-desc-bridge",
            description="",
        )
        assert bridge.description == ""

    def test_export_describe_consistency(self, sample_bridge):
        """Test that describe() returns valid JSON representation."""
        json_str = sample_bridge.describe()

        assert isinstance(json_str, str)
        assert "test-bridge" in json_str
        assert "test-compute" in json_str

    def test_clone_bridge(self, sample_bridge):
        """Test cloning a bridge with updates."""
        cloned = sample_bridge.clone(name="cloned-bridge")

        assert cloned.name == "cloned-bridge"
        assert cloned.compute_domain == sample_bridge.compute_domain
        assert cloned is not sample_bridge
