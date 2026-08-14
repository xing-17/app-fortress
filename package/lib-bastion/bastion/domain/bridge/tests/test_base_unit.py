"""
Unit tests for BaseBridgeModel.
"""

import pytest

from bastion.domain.bridge.base import BaseBridgeModel


class TestBaseBridgeModel:
    """Test suite for BaseBridgeModel."""

    def test_create_bridge_with_required_fields(self):
        """Test creating a bridge with only required fields."""
        bridge = BaseBridgeModel(name="test-bridge")

        assert bridge.name == "test-bridge"
        assert bridge.compute_name is None
        assert bridge.asset_names == []
        assert bridge.description is None
        assert bridge.metadata == {}
        assert bridge.tags == {}

    def test_create_bridge_with_all_fields(self):
        """Test creating a bridge with all fields."""
        bridge = BaseBridgeModel(
            name="data-bridge",
            compute_name="compute-01",
            asset_names=["asset-01", "asset-02"],
            description="Bridge for data processing",
            metadata={"priority": "high", "version": "1.0"},
            tags={"env": "prod", "team": "data"},
        )

        assert bridge.name == "data-bridge"
        assert bridge.compute_name == "compute-01"
        assert bridge.asset_names == ["asset-01", "asset-02"]
        assert bridge.description == "Bridge for data processing"
        assert bridge.metadata == {"priority": "high", "version": "1.0"}
        assert bridge.tags == {"env": "prod", "team": "data"}

    def test_export_bridge_data(self):
        """Test exporting bridge data to dictionary."""
        bridge = BaseBridgeModel(
            name="export-bridge",
            compute_name="compute-02",
            asset_names=["asset-03"],
            description="Test export",
            metadata={"key": "value"},
            tags={"env": "test"},
        )

        exported = bridge.export()

        assert exported["name"] == "export-bridge"
        assert exported["compute_name"] == "compute-02"
        assert exported["asset_names"] == ["asset-03"]
        assert exported["description"] == "Test export"
        assert exported["metadata"] == {"key": "value"}
        assert exported["tags"] == {"env": "test"}

    def test_bridge_asset_names_default(self):
        """Test that asset_names defaults to empty list."""
        bridge = BaseBridgeModel(name="test-bridge")

        assert isinstance(bridge.asset_names, list)
        assert len(bridge.asset_names) == 0

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

    def test_bridge_name_required(self):
        """Test that name field is required."""
        with pytest.raises(Exception):
            BaseBridgeModel()

    def test_export_maintains_none_values(self):
        """Test that export preserves None values for optional fields."""
        bridge = BaseBridgeModel(name="minimal-bridge")
        exported = bridge.export()

        assert exported["compute_name"] is None
        assert exported["description"] is None

    def test_from_any_with_dict(self):
        """Test from_any creates model from dictionary."""
        data = {
            "name": "test-bridge",
            "compute_name": "compute-01",
            "asset_names": ["asset-01", "asset-02"],
            "description": "Test bridge",
            "metadata": {"key": "value"},
            "tags": {"env": "test"},
        }
        bridge = BaseBridgeModel.from_any(data)
        assert bridge.name == "test-bridge"
        assert bridge.compute_name == "compute-01"
        assert bridge.asset_names == ["asset-01", "asset-02"]
        assert bridge.description == "Test bridge"
        assert bridge.metadata == {"key": "value"}
        assert bridge.tags == {"env": "test"}

    def test_from_any_with_model_instance(self):
        """Test from_any returns same instance when given model."""
        original = BaseBridgeModel(name="test-bridge")
        result = BaseBridgeModel.from_any(original)
        assert result is original

    def test_roundtrip_export_from_any(self):
        """Test export and from_any roundtrip conversion."""
        original = BaseBridgeModel(
            name="roundtrip-bridge",
            compute_name="compute-02",
            asset_names=["asset-03", "asset-04"],
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
        assert restored.compute_name == original.compute_name
        assert restored.asset_names == original.asset_names
        assert restored.description == original.description
        assert restored.metadata == original.metadata
        assert restored.tags == original.tags
