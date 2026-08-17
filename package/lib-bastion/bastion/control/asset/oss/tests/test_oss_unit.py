"""Unit tests for OSSAsset."""

from __future__ import annotations

import json

from bastion.control.asset.oss.oss import OSSAsset, OSSAssetModel
from bastion.domain.asset.base import AssetKind, AssetPlatform


class TestOSSAssetModel:
    """Test OSSAssetModel domain model."""

    def test_init_with_required_fields(self):
        """Test initialization with required fields."""
        model = OSSAssetModel(
            name="test_asset",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.OSS,
            bucket="test-bucket",
            prefix="data/test.parquet",
        )

        assert model.name == "test_asset"
        assert model.kind == AssetKind.PARQUET
        assert model.platform == AssetPlatform.OSS
        assert model.bucket == "test-bucket"
        assert model.prefix == "data/test.parquet"
        assert model.region is None

    def test_init_with_all_fields(self):
        """Test initialization with all fields."""
        model = OSSAssetModel(
            name="test_asset",
            kind=AssetKind.CSV,
            platform=AssetPlatform.OSS,
            bucket="test-bucket",
            prefix="data/test.csv",
            region="cn-hangzhou",
            description="Test OSS asset",
            owner="test_owner",
            metadata={"key": "value"},
            tags={"env": "prod"},
        )

        assert model.name == "test_asset"
        assert model.kind == AssetKind.CSV
        assert model.platform == AssetPlatform.OSS
        assert model.bucket == "test-bucket"
        assert model.prefix == "data/test.csv"
        assert model.region == "cn-hangzhou"
        assert model.description == "Test OSS asset"
        assert model.owner == "test_owner"
        assert model.metadata == {"key": "value"}
        assert model.tags == {"env": "prod"}

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "oss",
            "bucket": "test-bucket",
            "prefix": "data/test.parquet",
            "region": "cn-beijing",
        }

        model = OSSAssetModel.from_any(data)

        assert model.name == "test_asset"
        assert model.kind == AssetKind.PARQUET
        assert model.platform == AssetPlatform.OSS
        assert model.bucket == "test-bucket"
        assert model.prefix == "data/test.parquet"
        assert model.region == "cn-beijing"


class TestOSSAsset:
    """Test OSSAsset control layer."""

    def test_init_from_dict(self):
        """Test initialization from dictionary."""
        data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "oss",
            "bucket": "test-bucket",
            "prefix": "data/test.parquet",
        }

        asset = OSSAsset.from_dict(data)

        assert asset.name == "test_asset"
        assert asset.kind == "parquet"
        assert asset.platform == "oss"
        assert asset.bucket == "test-bucket"
        assert asset.prefix == "data/test.parquet"

    def test_init_from_domain_model(self):
        """Test initialization from domain model."""
        model = OSSAssetModel(
            name="test_asset",
            kind=AssetKind.CSV,
            platform=AssetPlatform.OSS,
            bucket="test-bucket",
            prefix="data/test.csv",
            region="cn-shanghai",
        )

        asset = OSSAsset.from_domain(model)

        assert asset.name == "test_asset"
        assert asset.kind == AssetKind.CSV
        assert asset.platform == AssetPlatform.OSS
        assert asset.bucket == "test-bucket"
        assert asset.prefix == "data/test.csv"
        assert asset.region == "cn-shanghai"

    def test_attribute_access(self):
        """Test attribute access via __getattr__."""
        asset = OSSAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "oss",
                "bucket": "test-bucket",
                "prefix": "data/test.parquet",
                "region": "cn-shenzhen",
                "description": "Test OSS asset",
                "owner": "data_team",
                "metadata": {"priority": "high"},
                "tags": {"env": "prod"},
            }
        )

        # Test all attributes
        assert asset.name == "test_asset"
        assert asset.kind == "parquet"
        assert asset.platform == "oss"
        assert asset.bucket == "test-bucket"
        assert asset.prefix == "data/test.parquet"
        assert asset.region == "cn-shenzhen"
        assert asset.description == "Test OSS asset"
        assert asset.owner == "data_team"
        assert asset.metadata == {"priority": "high"}
        assert asset.tags == {"env": "prod"}

    def test_get_location_uri_with_leading_slash(self):
        """Test get_location_uri strips leading slash from prefix."""
        asset = OSSAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "oss",
                "bucket": "test-bucket",
                "prefix": "/data/test.parquet",
            }
        )

        uri = asset.get_location_uri()

        assert uri == "oss://test-bucket/data/test.parquet"
        assert not uri.endswith("//data")

    def test_get_location_uri_without_leading_slash(self):
        """Test get_location_uri without leading slash in prefix."""
        asset = OSSAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "csv",
                "platform": "oss",
                "bucket": "my-bucket",
                "prefix": "folder/data.csv",
            }
        )

        uri = asset.get_location_uri()

        assert uri == "oss://my-bucket/folder/data.csv"

    def test_export(self):
        """Test export method."""
        asset = OSSAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "oss",
                "bucket": "test-bucket",
                "prefix": "data/test.parquet",
                "region": "cn-hangzhou",
                "description": "Test asset",
            }
        )

        data = asset.export()

        assert isinstance(data, dict)
        assert data["name"] == "test_asset"
        assert data["kind"] == "parquet"
        assert data["platform"] == "oss"
        assert data["bucket"] == "test-bucket"
        assert data["prefix"] == "data/test.parquet"
        assert data["region"] == "cn-hangzhou"
        assert data["description"] == "Test asset"

    def test_describe(self):
        """Test describe method."""
        asset = OSSAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "csv",
                "platform": "oss",
                "bucket": "test-bucket",
                "prefix": "data/test.csv",
            }
        )

        description = asset.describe()

        assert isinstance(description, str)

        # Should be valid JSON
        data = json.loads(description)
        assert data["name"] == "test_asset"
        assert data["kind"] == "csv"
        assert data["platform"] == "oss"
        assert data["bucket"] == "test-bucket"

    def test_domain_attribute(self):
        """Test direct access to domain attribute."""
        asset = OSSAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "oss",
                "bucket": "test-bucket",
                "prefix": "data/test.parquet",
            }
        )

        assert isinstance(asset.domain, OSSAssetModel)
        assert asset.domain.name == "test_asset"
        assert asset.domain.bucket == "test-bucket"

    def test_roundtrip_minimal_fields(self):
        """Test roundtrip with minimal fields."""
        original_data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "oss",
            "bucket": "test-bucket",
            "prefix": "data/test.parquet",
        }

        # Create asset from dict
        asset = OSSAsset.from_dict(original_data)

        # Export to dict
        exported = asset.export()

        # Create new asset from exported dict
        roundtrip_asset = OSSAsset.from_dict(exported)

        # Verify all fields match
        assert roundtrip_asset.name == asset.name
        assert roundtrip_asset.kind == asset.kind
        assert roundtrip_asset.platform == asset.platform
        assert roundtrip_asset.bucket == asset.bucket
        assert roundtrip_asset.prefix == asset.prefix
        assert roundtrip_asset.region == asset.region
        assert roundtrip_asset.description == asset.description
        assert roundtrip_asset.owner == asset.owner
        assert roundtrip_asset.metadata == asset.metadata
        assert roundtrip_asset.tags == asset.tags

    def test_roundtrip_full_fields(self):
        """Test roundtrip with all fields."""
        original_data = {
            "name": "full_oss_asset",
            "kind": "csv",
            "platform": "oss",
            "bucket": "production-oss-bucket",
            "prefix": "data/processed/output.csv",
            "region": "cn-hangzhou",
            "description": "Production OSS asset with full metadata",
            "owner": "data_engineering",
            "metadata": {
                "storage_type": "Standard",
                "acl": "private",
                "server_side_encryption": "AES256",
            },
            "tags": {
                "environment": "production",
                "department": "data-engineering",
                "compliance": "gdpr",
            },
        }

        # Create asset from dict
        asset = OSSAsset.from_dict(original_data)

        # Export to dict
        exported = asset.export()

        # Create new asset from exported dict
        roundtrip_asset = OSSAsset.from_dict(exported)

        # Verify all fields match
        assert roundtrip_asset.name == asset.name == "full_oss_asset"
        assert roundtrip_asset.kind == asset.kind == "csv"
        assert roundtrip_asset.platform == asset.platform == "oss"
        assert roundtrip_asset.bucket == asset.bucket == "production-oss-bucket"
        assert roundtrip_asset.prefix == asset.prefix == "data/processed/output.csv"
        assert roundtrip_asset.region == asset.region == "cn-hangzhou"
        assert (
            roundtrip_asset.description
            == asset.description
            == "Production OSS asset with full metadata"
        )
        assert roundtrip_asset.owner == asset.owner == "data_engineering"
        assert (
            roundtrip_asset.metadata
            == asset.metadata
            == {
                "storage_type": "Standard",
                "acl": "private",
                "server_side_encryption": "AES256",
            }
        )
        assert (
            roundtrip_asset.tags
            == asset.tags
            == {
                "environment": "production",
                "department": "data-engineering",
                "compliance": "gdpr",
            }
        )

    def test_export_equals_domain_export(self):
        """Test that asset.export() equals asset.domain.export()."""
        asset = OSSAsset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "oss",
                "bucket": "test-bucket",
                "prefix": "data/test.parquet",
                "region": "cn-shanghai",
                "description": "Test OSS asset",
                "metadata": {"acl": "public-read"},
            }
        )

        asset_export = asset.export()
        domain_export = asset.domain.model_dump(mode="json")

        assert asset_export == domain_export
