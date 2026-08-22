"""
Unit tests for S3Asset, S3AssetModel, and S3AssetRef classes.

Tests cover:
- S3AssetRef: URI parsing, bucket/prefix extraction
- S3AssetModel: Domain model validation
- S3Asset: Partition resolution, inspect method
"""

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from bastion.control.asset.s3.adaptor import IS3AdaptorLike, S3Adaptor
from bastion.control.asset.s3.s3 import S3Asset, S3AssetModel, S3AssetRef
from bastion.domain.assetkind import AssetKind
from bastion.domain.platform import Platform

warnings.filterwarnings("ignore")
pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ============================================================================
# S3AssetRef Tests
# ============================================================================


class TestS3AssetRef:
    """Test suite for S3AssetRef class."""

    def test_bucket_computed_field(self):
        """Test that bucket is extracted from S3 URI."""
        ref = S3AssetRef(
            uri="s3://my-bucket/path/to/file.parquet",
            partitions={},
            size=1024,
        )
        assert ref.bucket == "my-bucket"

    def test_prefix_computed_field(self):
        """Test that prefix is extracted from S3 URI."""
        ref = S3AssetRef(
            uri="s3://my-bucket/path/to/file.parquet",
            partitions={},
            size=1024,
        )
        assert ref.prefix == "path/to/file.parquet"

    def test_ref_with_nested_path(self):
        """Test S3AssetRef with deeply nested path."""
        ref = S3AssetRef(
            uri="s3://data-lake/raw/year=2024/month=01/day=15/data.parquet",
            partitions={"year": "2024", "month": "01", "day": "15"},
            size=4096,
        )
        assert ref.bucket == "data-lake"
        assert ref.prefix == "raw/year=2024/month=01/day=15/data.parquet"
        assert ref.partitions == {"year": "2024", "month": "01", "day": "15"}

    def test_ref_with_metadata(self):
        """Test S3AssetRef with all metadata fields."""
        modified = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        ref = S3AssetRef(
            uri="s3://my-bucket/data.parquet",
            partitions={"year": "2024"},
            size=8192,
            modified_at=modified,
            region="us-west-2",
            storage_class="STANDARD",
            etag="abc123",
        )

        assert ref.size == 8192
        assert ref.modified_at == modified
        assert ref.partitions == {"year": "2024"}
        assert ref.region == "us-west-2"
        assert ref.storage_class == "STANDARD"
        assert ref.etag == "abc123"

    def test_ref_without_partitions(self):
        """Test S3AssetRef with empty partitions."""
        ref = S3AssetRef(
            uri="s3://my-bucket/simple.csv",
            partitions={},
            size=512,
        )
        assert ref.partitions == {}
        assert ref.bucket == "my-bucket"
        assert ref.prefix == "simple.csv"

    def test_ref_with_root_path(self):
        """Test S3AssetRef with file at bucket root."""
        ref = S3AssetRef(
            uri="s3://my-bucket/file.txt",
            partitions={},
            size=256,
        )
        assert ref.bucket == "my-bucket"
        assert ref.prefix == "file.txt"

    def test_ref_invalid_uri_raises_on_access(self):
        """Test S3AssetRef with invalid URI scheme raises error on property access."""
        ref = S3AssetRef(
            uri="http://invalid/path",
            partitions={},
            size=1024,
        )
        # Error is raised when accessing computed field
        with pytest.raises(ValueError, match="Invalid S3 URI"):
            _ = ref.bucket


# ============================================================================
# S3AssetModel Tests
# ============================================================================


class TestS3AssetModel:
    """Test suite for S3AssetModel domain model."""

    def test_model_creation_with_required_fields(self):
        """Test creating a model with all required fields."""
        model = S3AssetModel(
            name="test_asset",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
        )

        assert model.name == "test_asset"
        assert model.uri == "s3://my-bucket/data/"
        assert model.kind == AssetKind.PARQUET
        assert model.platform == Platform.S3

    def test_model_platform_defaults_to_s3(self):
        """Test that platform defaults to S3."""
        model = S3AssetModel(
            name="sales",
            uri="s3://data-bucket/sales/",
            kind=AssetKind.CSV,
        )
        assert model.platform == Platform.S3

    def test_model_bucket_computed_field(self):
        """Test bucket computed field."""
        model = S3AssetModel(
            name="test",
            uri="s3://my-bucket/path/to/data/",
            kind=AssetKind.PARQUET,
        )
        assert model.bucket == "my-bucket"

    def test_model_prefix_computed_field(self):
        """Test prefix computed field."""
        model = S3AssetModel(
            name="test",
            uri="s3://my-bucket/path/to/data/",
            kind=AssetKind.PARQUET,
        )
        assert model.prefix == "path/to/data/"

    def test_model_with_region(self):
        """Test model with AWS region."""
        model = S3AssetModel(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            region="us-west-2",
        )
        assert model.region == "us-west-2"

    def test_model_with_partitions(self):
        """Test model with partition columns."""
        model = S3AssetModel(
            name="partitioned_data",
            uri="s3://data-lake/warehouse/",
            kind=AssetKind.PARQUET,
            partitions=["year", "month", "day"],
        )

        assert model.partitions == ["year", "month", "day"]

    def test_model_with_metadata(self):
        """Test model with optional metadata fields."""
        model = S3AssetModel(
            name="enriched_asset",
            uri="s3://my-bucket/enriched/",
            kind=AssetKind.PARQUET,
            description="Test asset with metadata",
            owner="data_team",
            tags={"env": "test", "category": "demo"},
        )

        assert model.description == "Test asset with metadata"
        assert model.owner == "data_team"
        assert model.tags == {"env": "test", "category": "demo"}

    def test_model_with_refs(self):
        """Test model with file references."""
        ref = S3AssetRef(
            uri="s3://my-bucket/data/file.parquet",
            partitions={},
            size=1024,
        )

        model = S3AssetModel(
            name="asset_with_refs",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            refs=[ref],
        )

        assert len(model.refs) == 1
        assert model.refs[0].uri == "s3://my-bucket/data/file.parquet"


# ============================================================================
# S3Asset Tests
# ============================================================================


class TestS3AssetResolvePartition:
    """Test suite for S3Asset._resolve_partition method."""

    def test_resolve_partition_no_partitions(self):
        """Test partition resolution when no partitions defined."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        result = asset._resolve_partition("data/file.parquet")
        assert result == {}

    def test_resolve_partition_single(self):
        """Test resolving a single partition."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year"],
        )

        result = asset._resolve_partition("data/year=2024/file.parquet")
        assert result == {"year": "2024"}

    def test_resolve_partition_multiple(self):
        """Test resolving multiple partitions."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year", "month", "day"],
        )

        result = asset._resolve_partition("data/year=2024/month=01/day=15/file.parquet")
        assert result == {"year": "2024", "month": "01", "day": "15"}

    def test_resolve_partition_subset(self):
        """Test resolving when only some partitions are present."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year", "month", "day"],
        )

        # Only year and month in path
        result = asset._resolve_partition("data/year=2024/month=01/file.parquet")
        assert result == {"year": "2024", "month": "01"}

    def test_resolve_partition_with_prefix(self):
        """Test partition resolution with non-empty prefix."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/raw/sales/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["region"],
        )

        result = asset._resolve_partition("raw/sales/region=us/data.parquet")
        assert result == {"region": "us"}

    def test_resolve_partition_extra_dirs(self):
        """Test handling paths with non-partition directories."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year"],
        )

        # Has subdirectories that aren't partitions
        result = asset._resolve_partition("data/year=2024/subdir/file.parquet")
        assert result == {"year": "2024"}


# ============================================================================
# S3Asset.inspect Tests (with mocking)
# ============================================================================


class TestS3AssetInspect:
    """Test suite for S3Asset.inspect method with mocked adaptor."""

    def test_inspect_basic(self):
        """Test basic inspect functionality."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        # Mock adaptor
        mock_adaptor = MagicMock(spec=IS3AdaptorLike)
        mock_adaptor.list_objects.return_value = [
            {
                "Key": "data/file1.parquet",
                "Size": 1024,
                "LastModified": datetime(2024, 1, 1, tzinfo=UTC),
                "ETag": "etag1",
                "StorageClass": "STANDARD",
            },
            {
                "Key": "data/file2.parquet",
                "Size": 2048,
                "LastModified": datetime(2024, 1, 2, tzinfo=UTC),
                "ETag": "etag2",
                "StorageClass": "STANDARD",
            },
        ]

        refs = asset.inspect(adaptor=mock_adaptor)

        assert len(refs) == 2
        assert refs[0].uri == "s3://my-bucket/data/file1.parquet"
        assert refs[0].size == 1024
        assert refs[1].uri == "s3://my-bucket/data/file2.parquet"
        assert refs[1].size == 2048

        # Check that list_objects was called with correct parameters
        mock_adaptor.list_objects.assert_called_once_with(
            bucket="my-bucket",
            prefix="data/",
            since=None,
            until=None,
            limit=None,
        )

    def test_inspect_with_partitions(self):
        """Test inspect with partitioned data."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year", "month"],
        )

        mock_adaptor = MagicMock(spec=IS3AdaptorLike)
        mock_adaptor.list_objects.return_value = [
            {
                "Key": "data/year=2024/month=01/file1.parquet",
                "Size": 1024,
                "LastModified": datetime(2024, 1, 1, tzinfo=UTC),
            },
            {
                "Key": "data/year=2024/month=02/file2.parquet",
                "Size": 2048,
                "LastModified": datetime(2024, 2, 1, tzinfo=UTC),
            },
        ]

        refs = asset.inspect(adaptor=mock_adaptor)

        assert len(refs) == 2
        assert refs[0].partitions == {"year": "2024", "month": "01"}
        assert refs[1].partitions == {"year": "2024", "month": "02"}

    def test_inspect_with_time_filters(self):
        """Test inspect with time filtering."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        mock_adaptor = MagicMock(spec=IS3AdaptorLike)
        mock_adaptor.list_objects.return_value = [
            {
                "Key": "data/file.parquet",
                "Size": 1024,
                "LastModified": datetime(2024, 1, 5, tzinfo=UTC),
            },
        ]

        since = datetime(2024, 1, 1, tzinfo=UTC)
        until = datetime(2024, 1, 10, tzinfo=UTC)

        _ = asset.inspect(adaptor=mock_adaptor, since=since, until=until)

        # Verify parameters passed to list_objects
        mock_adaptor.list_objects.assert_called_once_with(
            bucket="my-bucket",
            prefix="data/",
            since=since,
            until=until,
            limit=None,
        )

    def test_inspect_with_limit(self):
        """Test inspect with result limit."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        mock_adaptor = MagicMock(spec=IS3AdaptorLike)
        mock_adaptor.list_objects.return_value = [
            {
                "Key": f"data/file{i}.parquet",
                "Size": 1024,
                "LastModified": datetime(2024, 1, i, tzinfo=UTC),
            }
            for i in range(1, 4)
        ]

        refs = asset.inspect(adaptor=mock_adaptor, limit=3)

        assert len(refs) == 3
        mock_adaptor.list_objects.assert_called_once_with(
            bucket="my-bucket",
            prefix="data/",
            since=None,
            until=None,
            limit=3,
        )

    def test_inspect_empty_bucket(self):
        """Test inspect with no matching files."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        mock_adaptor = MagicMock(spec=IS3AdaptorLike)
        mock_adaptor.list_objects.return_value = []

        refs = asset.inspect(adaptor=mock_adaptor)

        assert refs == []

    def test_inspect_updates_domain_refs(self):
        """Test that inspect updates the asset's domain refs."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        mock_adaptor = MagicMock(spec=IS3AdaptorLike)
        mock_adaptor.list_objects.return_value = [
            {
                "Key": "data/file.parquet",
                "Size": 1024,
                "LastModified": datetime(2024, 1, 1, tzinfo=UTC),
            },
        ]

        refs = asset.inspect(adaptor=mock_adaptor)

        # Check that domain.refs was updated
        assert len(asset.domain.refs) == 1
        assert asset.domain.refs[0] == refs[0]

    def test_inspect_with_region(self):
        """Test inspect with AWS region."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            region="us-west-2",
        )

        mock_adaptor = MagicMock(spec=IS3AdaptorLike)
        mock_adaptor.list_objects.return_value = [
            {
                "Key": "data/file.parquet",
                "Size": 1024,
                "LastModified": datetime(2024, 1, 1, tzinfo=UTC),
            },
        ]

        refs = asset.inspect(adaptor=mock_adaptor)

        assert refs[0].region == "us-west-2"

    def test_inspect_default_adaptor(self):
        """Test inspect creates default adaptor when none provided."""
        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        # Mock the S3Adaptor's list_objects method
        with patch.object(S3Adaptor, "list_objects", return_value=[]):
            refs = asset.inspect()
            # Should not raise an error
            assert refs == []
