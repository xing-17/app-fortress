"""Unit tests for LocalAsset."""

from __future__ import annotations

import json
from pathlib import Path

from bastion.control.asset.local.local import LocalAsset, LocalAssetModel
from bastion.domain.asset.base import AssetKind, AssetPlatform


class TestLocalAssetModel:
    """Test LocalAssetModel domain model."""

    def test_init_with_required_fields(self):
        """Test initialization with required fields."""
        model = LocalAssetModel(
            name="test_asset",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.LOCAL,
            path="/tmp/test.parquet",
        )

        assert model.name == "test_asset"
        assert model.kind == AssetKind.PARQUET
        assert model.platform == AssetPlatform.LOCAL
        assert model.path == "/tmp/test.parquet"

    def test_init_with_all_fields(self):
        """Test initialization with all fields."""
        model = LocalAssetModel(
            name="test_asset",
            kind=AssetKind.CSV,
            platform=AssetPlatform.LOCAL,
            path="/tmp/test.csv",
            description="Test description",
            owner="test_owner",
            metadata={"key": "value"},
            tags={"env": "test"},
        )

        assert model.name == "test_asset"
        assert model.kind == AssetKind.CSV
        assert model.platform == AssetPlatform.LOCAL
        assert model.path == "/tmp/test.csv"
        assert model.description == "Test description"
        assert model.owner == "test_owner"
        assert model.metadata == {"key": "value"}
        assert model.tags == {"env": "test"}

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "local",
            "path": "/tmp/test.parquet",
        }

        model = LocalAssetModel.from_any(data)

        assert model.name == "test_asset"
        assert model.kind == AssetKind.PARQUET
        assert model.platform == AssetPlatform.LOCAL
        assert model.path == "/tmp/test.parquet"


class TestLocalAsset:
    """Test LocalAsset control layer."""

    def test_init_from_dict(self):
        """Test initialization from dictionary."""
        data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "local",
            "path": "/tmp/test.parquet",
        }

        asset = LocalAsset.from_dict(data)

        assert asset.name == "test_asset"
        assert asset.kind == "parquet"
        assert asset.platform == "local"
        assert asset.path == "/tmp/test.parquet"

    def test_init_from_domain_model(self):
        """Test initialization from domain model."""
        model = LocalAssetModel(
            name="test_asset",
            kind=AssetKind.CSV,
            platform=AssetPlatform.LOCAL,
            path="/tmp/test.csv",
        )

        asset = LocalAsset.from_domain(model)

        assert asset.name == "test_asset"
        assert asset.kind == AssetKind.CSV
        assert asset.platform == AssetPlatform.LOCAL
        assert asset.path == "/tmp/test.csv"

    def test_attribute_access(self):
        """Test attribute access via __getattr__."""
        asset = LocalAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "local",
                "path": "/tmp/test.parquet",
                "description": "Test description",
                "owner": "test_owner",
                "metadata": {"priority": "high"},
                "tags": {"env": "prod"},
            }
        )

        # Test all attributes
        assert asset.name == "test_asset"
        assert asset.kind == "parquet"
        assert asset.platform == "local"
        assert asset.path == "/tmp/test.parquet"
        assert asset.description == "Test description"
        assert asset.owner == "test_owner"
        assert asset.metadata == {"priority": "high"}
        assert asset.tags == {"env": "prod"}

    def test_get_location_uri(self):
        """Test get_location_uri method."""
        asset = LocalAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "local",
                "path": "/tmp/test.parquet",
            }
        )

        uri = asset.get_location_uri()

        # Should return resolved absolute path
        assert uri.endswith("test.parquet")
        assert Path(uri).is_absolute()

    def test_get_location_uri_with_home_expansion(self):
        """Test get_location_uri with ~ expansion."""
        asset = LocalAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "csv",
                "platform": "local",
                "path": "~/data/test.csv",
            }
        )

        uri = asset.get_location_uri()

        # Should expand ~ and resolve to absolute path
        assert "~" not in uri
        assert Path(uri).is_absolute()

    def test_export(self):
        """Test export method."""
        asset = LocalAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "local",
                "path": "/tmp/test.parquet",
                "description": "Test asset",
                "metadata": {"key": "value"},
            }
        )

        data = asset.export()

        assert isinstance(data, dict)
        assert data["name"] == "test_asset"
        assert data["kind"] == "parquet"
        assert data["platform"] == "local"
        assert data["path"] == "/tmp/test.parquet"
        assert data["description"] == "Test asset"
        assert data["metadata"] == {"key": "value"}

    def test_describe(self):
        """Test describe method."""
        asset = LocalAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "csv",
                "platform": "local",
                "path": "/tmp/test.csv",
            }
        )

        description = asset.describe()

        assert isinstance(description, str)

        # Should be valid JSON
        data = json.loads(description)
        assert data["name"] == "test_asset"
        assert data["kind"] == "csv"
        assert data["platform"] == "local"

    def test_domain_attribute(self):
        """Test direct access to domain attribute."""
        asset = LocalAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "local",
                "path": "/tmp/test.parquet",
            }
        )

        assert isinstance(asset.domain, LocalAssetModel)
        assert asset.domain.name == "test_asset"

    def test_roundtrip_minimal_fields(self):
        """Test roundtrip with minimal fields."""
        original_data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "local",
            "path": "/tmp/test.parquet",
        }

        # Create asset from dict
        asset = LocalAsset.from_dict(original_data)

        # Export to dict
        exported = asset.export()

        # Create new asset from exported dict
        roundtrip_asset = LocalAsset.from_dict(exported)

        # Verify all fields match
        assert roundtrip_asset.name == asset.name
        assert roundtrip_asset.kind == asset.kind
        assert roundtrip_asset.platform == asset.platform
        assert roundtrip_asset.path == asset.path
        assert roundtrip_asset.description == asset.description
        assert roundtrip_asset.owner == asset.owner
        assert roundtrip_asset.metadata == asset.metadata
        assert roundtrip_asset.tags == asset.tags

    def test_roundtrip_full_fields(self):
        """Test roundtrip with all fields."""
        original_data = {
            "name": "full_test_asset",
            "kind": "csv",
            "platform": "local",
            "path": "~/data/test.csv",
            "description": "Full test asset with all fields",
            "owner": "data_team",
            "metadata": {
                "priority": "high",
                "size": "large",
                "version": "v1.2.3",
            },
            "tags": {
                "env": "production",
                "team": "analytics",
                "project": "ml-pipeline",
            },
        }

        # Create asset from dict
        asset = LocalAsset.from_dict(original_data)

        # Export to dict
        exported = asset.export()

        # Create new asset from exported dict
        roundtrip_asset = LocalAsset.from_dict(exported)

        # Verify all fields match
        assert roundtrip_asset.name == asset.name == "full_test_asset"
        assert roundtrip_asset.kind == asset.kind == "csv"
        assert roundtrip_asset.platform == asset.platform == "local"
        assert roundtrip_asset.path == asset.path == "~/data/test.csv"
        assert roundtrip_asset.description == asset.description == "Full test asset with all fields"
        assert roundtrip_asset.owner == asset.owner == "data_team"
        assert (
            roundtrip_asset.metadata
            == asset.metadata
            == {
                "priority": "high",
                "size": "large",
                "version": "v1.2.3",
            }
        )
        assert (
            roundtrip_asset.tags
            == asset.tags
            == {
                "env": "production",
                "team": "analytics",
                "project": "ml-pipeline",
            }
        )

    def test_export_equals_domain_export(self):
        """Test that asset.export() equals asset.domain.export()."""
        asset = LocalAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "local",
                "path": "/tmp/test.parquet",
                "description": "Test asset",
                "metadata": {"key": "value"},
            }
        )

        asset_export = asset.export()
        domain_export = asset.domain.model_dump(mode="json")

        assert asset_export == domain_export
