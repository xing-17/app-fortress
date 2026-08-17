"""Unit tests for S3Asset."""

from __future__ import annotations

import json

from bastion.control.asset.s3.s3 import S3Asset, S3AssetModel
from bastion.domain.asset.base import AssetKind, AssetPlatform


class TestS3AssetModel:
    """Test S3AssetModel domain model."""

    def test_init_with_required_fields(self):
        """Test initialization with required fields."""
        model = S3AssetModel(
            name="test_asset",
            kind=AssetKind.PARQUET,
            platform=AssetPlatform.S3,
            bucket="test-bucket",
            prefix="data/test.parquet",
        )

        assert model.name == "test_asset"
        assert model.kind == AssetKind.PARQUET
        assert model.platform == AssetPlatform.S3
        assert model.bucket == "test-bucket"
        assert model.prefix == "data/test.parquet"
        assert model.region is None

    def test_init_with_all_fields(self):
        """Test initialization with all fields."""
        model = S3AssetModel(
            name="test_asset",
            kind=AssetKind.CSV,
            platform=AssetPlatform.S3,
            bucket="test-bucket",
            prefix="data/test.csv",
            region="us-west-2",
            description="Test S3 asset",
            owner="test_owner",
            metadata={"key": "value"},
            tags={"env": "prod"},
        )

        assert model.name == "test_asset"
        assert model.kind == AssetKind.CSV
        assert model.platform == AssetPlatform.S3
        assert model.bucket == "test-bucket"
        assert model.prefix == "data/test.csv"
        assert model.region == "us-west-2"
        assert model.description == "Test S3 asset"
        assert model.owner == "test_owner"
        assert model.metadata == {"key": "value"}
        assert model.tags == {"env": "prod"}

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "s3",
            "bucket": "test-bucket",
            "prefix": "data/test.parquet",
            "region": "ap-northeast-1",
        }

        model = S3AssetModel.from_any(data)

        assert model.name == "test_asset"
        assert model.kind == AssetKind.PARQUET
        assert model.platform == AssetPlatform.S3
        assert model.bucket == "test-bucket"
        assert model.prefix == "data/test.parquet"
        assert model.region == "ap-northeast-1"


class TestS3Asset:
    """Test S3Asset control layer."""

    def test_init_from_dict(self):
        """Test initialization from dictionary."""
        data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "s3",
            "bucket": "test-bucket",
            "prefix": "data/test.parquet",
        }

        asset = S3Asset.from_dict(data)

        assert asset.name == "test_asset"
        assert asset.kind == "parquet"
        assert asset.platform == "s3"
        assert asset.bucket == "test-bucket"
        assert asset.prefix == "data/test.parquet"

    def test_init_from_domain_model(self):
        """Test initialization from domain model."""
        model = S3AssetModel(
            name="test_asset",
            kind=AssetKind.CSV,
            platform=AssetPlatform.S3,
            bucket="test-bucket",
            prefix="data/test.csv",
            region="us-east-1",
        )

        asset = S3Asset.from_domain(model)

        assert asset.name == "test_asset"
        assert asset.kind == AssetKind.CSV
        assert asset.platform == AssetPlatform.S3
        assert asset.bucket == "test-bucket"
        assert asset.prefix == "data/test.csv"
        assert asset.region == "us-east-1"

    def test_attribute_access(self):
        """Test attribute access via __getattr__."""
        asset = S3Asset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "s3",
                "bucket": "test-bucket",
                "prefix": "data/test.parquet",
                "region": "eu-west-1",
                "description": "Test S3 asset",
                "owner": "data_team",
                "metadata": {"priority": "high"},
                "tags": {"env": "prod"},
            }
        )

        # Test all attributes
        assert asset.name == "test_asset"
        assert asset.kind == "parquet"
        assert asset.platform == "s3"
        assert asset.bucket == "test-bucket"
        assert asset.prefix == "data/test.parquet"
        assert asset.region == "eu-west-1"
        assert asset.description == "Test S3 asset"
        assert asset.owner == "data_team"
        assert asset.metadata == {"priority": "high"}
        assert asset.tags == {"env": "prod"}

    def test_get_location_uri_with_leading_slash(self):
        """Test get_location_uri strips leading slash from prefix."""
        asset = S3Asset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "s3",
                "bucket": "test-bucket",
                "prefix": "/data/test.parquet",
            }
        )

        uri = asset.get_location_uri()

        assert uri == "s3://test-bucket/data/test.parquet"
        assert not uri.endswith("//data")

    def test_get_location_uri_without_leading_slash(self):
        """Test get_location_uri without leading slash in prefix."""
        asset = S3Asset.from_dict(
            {
                "name": "test_asset",
                "kind": "csv",
                "platform": "s3",
                "bucket": "my-bucket",
                "prefix": "folder/data.csv",
            }
        )

        uri = asset.get_location_uri()

        assert uri == "s3://my-bucket/folder/data.csv"

    def test_export(self):
        """Test export method."""
        asset = S3Asset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "s3",
                "bucket": "test-bucket",
                "prefix": "data/test.parquet",
                "region": "us-west-2",
                "description": "Test asset",
            }
        )

        data = asset.export()

        assert isinstance(data, dict)
        assert data["name"] == "test_asset"
        assert data["kind"] == "parquet"
        assert data["platform"] == "s3"
        assert data["bucket"] == "test-bucket"
        assert data["prefix"] == "data/test.parquet"
        assert data["region"] == "us-west-2"
        assert data["description"] == "Test asset"

    def test_describe(self):
        """Test describe method."""
        asset = S3Asset.from_dict(
            {
                "name": "test_asset",
                "kind": "csv",
                "platform": "s3",
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
        assert data["platform"] == "s3"
        assert data["bucket"] == "test-bucket"

    def test_domain_attribute(self):
        """Test direct access to domain attribute."""
        asset = S3Asset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "s3",
                "bucket": "test-bucket",
                "prefix": "data/test.parquet",
            }
        )

        assert isinstance(asset.domain, S3AssetModel)
        assert asset.domain.name == "test_asset"
        assert asset.domain.bucket == "test-bucket"

    def test_roundtrip_minimal_fields(self):
        """Test roundtrip with minimal fields."""
        original_data = {
            "name": "test_asset",
            "kind": "parquet",
            "platform": "s3",
            "bucket": "test-bucket",
            "prefix": "data/test.parquet",
        }

        # Create asset from dict
        asset = S3Asset.from_dict(original_data)

        # Export to dict
        exported = asset.export()

        # Create new asset from exported dict
        roundtrip_asset = S3Asset.from_dict(exported)

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
            "name": "full_s3_asset",
            "kind": "csv",
            "platform": "s3",
            "bucket": "production-data-bucket",
            "prefix": "analytics/processed/data.csv",
            "region": "us-west-2",
            "description": "Production S3 asset with complete metadata",
            "owner": "analytics_team",
            "metadata": {
                "storage_class": "STANDARD",
                "encryption": "AES256",
                "version_id": "abc123",
            },
            "tags": {
                "environment": "production",
                "cost_center": "analytics",
                "data_classification": "confidential",
            },
        }

        # Create asset from dict
        asset = S3Asset.from_dict(original_data)

        # Export to dict
        exported = asset.export()

        # Create new asset from exported dict
        roundtrip_asset = S3Asset.from_dict(exported)

        # Verify all fields match
        assert roundtrip_asset.name == asset.name == "full_s3_asset"
        assert roundtrip_asset.kind == asset.kind == "csv"
        assert roundtrip_asset.platform == asset.platform == "s3"
        assert roundtrip_asset.bucket == asset.bucket == "production-data-bucket"
        assert roundtrip_asset.prefix == asset.prefix == "analytics/processed/data.csv"
        assert roundtrip_asset.region == asset.region == "us-west-2"
        assert (
            roundtrip_asset.description
            == asset.description
            == "Production S3 asset with complete metadata"
        )
        assert roundtrip_asset.owner == asset.owner == "analytics_team"
        assert (
            roundtrip_asset.metadata
            == asset.metadata
            == {
                "storage_class": "STANDARD",
                "encryption": "AES256",
                "version_id": "abc123",
            }
        )
        assert (
            roundtrip_asset.tags
            == asset.tags
            == {
                "environment": "production",
                "cost_center": "analytics",
                "data_classification": "confidential",
            }
        )

    def test_export_equals_domain_export(self):
        """Test that asset.export() equals asset.domain.export()."""
        asset = S3Asset.from_dict(
            {
                "name": "test_asset",
                "kind": "parquet",
                "platform": "s3",
                "bucket": "test-bucket",
                "prefix": "data/test.parquet",
                "region": "eu-west-1",
                "description": "Test S3 asset",
                "metadata": {"encryption": "enabled"},
            }
        )

        asset_export = asset.export()
        domain_export = asset.domain.model_dump(mode="json")

        assert asset_export == domain_export
