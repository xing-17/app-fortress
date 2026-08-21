"""
Comprehensive unit tests for S3Asset, S3AssetModel, and S3AssetRef classes.

Tests cover:
- S3AssetRef: URI parsing, bucket/prefix extraction, metadata fields
- S3AssetModel: Domain model validation, computed fields
- S3Asset: Client creation, pagination, partition extraction, inspection
- Error handling: Invalid URIs, boto3 errors, pagination failures
- Edge cases: Empty buckets, large result sets, special characters
- Integration: Complete workflows with mocked AWS responses
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from bastion.control.asset.s3.s3 import (
    S3Asset,
    S3AssetModel,
    S3AssetRef,
)
from bastion.domain.assetkind import AssetKind
from bastion.domain.platform import Platform


# ============================================================================
# S3AssetRef Tests
# ============================================================================


class TestS3AssetRef:
    """Test suite for S3AssetRef class."""

    def test_bucket_computed_field(self):
        """Test that bucket returns the bucket name from s3:// URI."""
        ref = S3AssetRef(
            uri="s3://my-bucket/path/to/object.parquet",
            partitions={},
            size=1024,
        )
        assert ref.bucket == "my-bucket"

    def test_prefix_computed_field(self):
        """Test that prefix returns the key path without leading slash."""
        ref = S3AssetRef(
            uri="s3://my-bucket/path/to/object.parquet",
            partitions={},
            size=1024,
        )
        assert ref.prefix == "path/to/object.parquet"

    def test_bucket_and_prefix_with_nested_path(self):
        """Test bucket and prefix extraction from deeply nested path."""
        ref = S3AssetRef(
            uri="s3://data-warehouse/year=2024/month=03/day=15/data.parquet",
            partitions={"year": "2024", "month": "03", "day": "15"},
            size=4096,
        )
        assert ref.bucket == "data-warehouse"
        assert ref.prefix == "year=2024/month=03/day=15/data.parquet"

    def test_invalid_uri_scheme_raises_error(self):
        """Test that non-S3 URI schemes raise ValueError."""
        with pytest.raises(ValueError, match="Invalid S3 URI"):
            S3AssetRef(
                uri="http://example.com/data.parquet",
                partitions={},
                size=1024,
            ).bucket

    def test_invalid_uri_scheme_in_prefix_raises_error(self):
        """Test that non-S3 URI schemes raise ValueError for prefix."""
        with pytest.raises(ValueError, match="Invalid S3 URI"):
            S3AssetRef(
                uri="file:///local/path/data.parquet",
                partitions={},
                size=1024,
            ).prefix

    def test_ref_with_all_metadata(self):
        """Test S3AssetRef with all optional fields."""
        modified = datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc)

        ref = S3AssetRef(
            uri="s3://my-bucket/data/file.parquet",
            partitions={"year": "2024"},
            size=8192,
            modified_at=modified,
            region="us-west-2",
            storage_class="STANDARD_IA",
            etag='"abc123def456"',
        )

        assert ref.size == 8192
        assert ref.modified_at == modified
        assert ref.region == "us-west-2"
        assert ref.storage_class == "STANDARD_IA"
        assert ref.etag == '"abc123def456"'
        assert ref.partitions == {"year": "2024"}

    def test_ref_without_optional_fields(self):
        """Test S3AssetRef with minimal required fields."""
        ref = S3AssetRef(
            uri="s3://bucket/key",
            partitions={},
            size=0,
        )
        assert ref.region is None
        assert ref.storage_class is None
        assert ref.etag is None
        assert ref.modified_at is None

    def test_prefix_strips_leading_slash(self):
        """Test that prefix removes leading slash if present."""
        ref = S3AssetRef(
            uri="s3://bucket//path/with/double/slash.parquet",
            partitions={},
            size=1024,
        )
        # urlparse should handle this, but prefix strips leading /
        assert not ref.prefix.startswith("/")

    def test_bucket_with_dots(self):
        """Test bucket names with dots (DNS-compatible)."""
        ref = S3AssetRef(
            uri="s3://my.bucket.name/data/file.parquet",
            partitions={},
            size=1024,
        )
        assert ref.bucket == "my.bucket.name"

    def test_bucket_with_hyphens(self):
        """Test bucket names with hyphens."""
        ref = S3AssetRef(
            uri="s3://my-bucket-name-123/data/file.parquet",
            partitions={},
            size=1024,
        )
        assert ref.bucket == "my-bucket-name-123"


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
        """Test that platform is set to S3."""
        model = S3AssetModel(
            name="sales",
            uri="s3://data-lake/sales/",
            kind=AssetKind.CSV,
        )
        assert model.platform == Platform.S3

    def test_model_bucket_computed_field(self):
        """Test that bucket is computed from URI."""
        model = S3AssetModel(
            name="test",
            uri="s3://my-bucket/prefix/path/",
            kind=AssetKind.PARQUET,
        )
        assert model.bucket == "my-bucket"

    def test_model_prefix_computed_field(self):
        """Test that prefix is computed from URI."""
        model = S3AssetModel(
            name="test",
            uri="s3://my-bucket/data/warehouse/sales/",
            kind=AssetKind.PARQUET,
        )
        assert model.prefix == "data/warehouse/sales/"

    def test_model_with_region(self):
        """Test model with AWS region specified."""
        model = S3AssetModel(
            name="regional_data",
            uri="s3://us-west-bucket/data/",
            kind=AssetKind.PARQUET,
            region="us-west-2",
        )
        assert model.region == "us-west-2"

    def test_model_with_partitions(self):
        """Test model with partition columns."""
        model = S3AssetModel(
            name="partitioned_data",
            uri="s3://warehouse/tables/sales/",
            kind=AssetKind.PARQUET,
            partitions=["year", "month", "day"],
        )
        assert model.partitions == ["year", "month", "day"]

    def test_model_with_metadata(self):
        """Test model with optional metadata fields."""
        model = S3AssetModel(
            name="enriched_asset",
            uri="s3://data-lake/enriched/",
            kind=AssetKind.PARQUET,
            description="Test S3 asset with metadata",
            owner="data_team",
            tags={"env": "prod", "category": "analytics"},
        )

        assert model.description == "Test S3 asset with metadata"
        assert model.owner == "data_team"
        assert model.tags == {"env": "prod", "category": "analytics"}

    def test_model_with_refs(self):
        """Test model with file references."""
        ref = S3AssetRef(
            uri="s3://bucket/data/file.parquet",
            partitions={},
            size=1024,
        )

        model = S3AssetModel(
            name="asset_with_refs",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            refs=[ref],
        )

        assert len(model.refs) == 1
        assert model.refs[0].uri == "s3://bucket/data/file.parquet"

    def test_model_invalid_uri_scheme_raises_error(self):
        """Test that invalid URI scheme raises error when accessing bucket."""
        model = S3AssetModel(
            name="invalid",
            uri="https://bucket.s3.amazonaws.com/data/",
            kind=AssetKind.PARQUET,
        )

        with pytest.raises(ValueError, match="Invalid S3 URI"):
            _ = model.bucket

    def test_model_empty_prefix(self):
        """Test model with bucket root (empty prefix)."""
        model = S3AssetModel(
            name="root_data",
            uri="s3://my-bucket/",
            kind=AssetKind.PARQUET,
        )
        assert model.bucket == "my-bucket"
        assert model.prefix == ""


# ============================================================================
# S3Asset Tests - Helper Methods
# ============================================================================


class TestS3AssetParsePartition:
    """Test suite for S3Asset._parse_partition method."""

    def test_parse_single_partition(self):
        """Test extracting a single partition value from S3 key."""
        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year"],
        )

        key = "data/year=2024/file.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"year": "2024"}

    def test_parse_multiple_partitions(self):
        """Test extracting multiple partition values."""
        asset = S3Asset(
            name="test",
            uri="s3://bucket/warehouse/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year", "month", "day"],
        )

        key = "warehouse/year=2024/month=03/day=15/data.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"year": "2024", "month": "03", "day": "15"}

    def test_parse_partition_with_no_partitions(self):
        """Test that non-partitioned assets return empty dict."""
        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.CSV,
            platform=Platform.S3,
        )

        key = "data/file.csv"
        partitions = asset._parse_partition(key)

        assert partitions == {}

    def test_parse_partition_ignores_non_partition_dirs(self):
        """Test that non-partition directories are ignored."""
        asset = S3Asset(
            name="test",
            uri="s3://bucket/warehouse/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year", "month"],
        )

        key = "warehouse/other/year=2024/month=06/file.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"year": "2024", "month": "06"}
        assert "other" not in partitions

    def test_parse_partition_with_special_characters(self):
        """Test partition extraction with special characters in values."""
        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["region", "category"],
        )

        key = "data/region=us-west-1/category=tech_hardware/data.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"region": "us-west-1", "category": "tech_hardware"}

    def test_parse_partition_only_extracts_defined_partitions(self):
        """Test that only defined partition columns are extracted."""
        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year"],
        )

        key = "data/year=2024/month=03/file.parquet"
        partitions = asset._parse_partition(key)

        # Should only extract 'year', not 'month'
        assert partitions == {"year": "2024"}
        assert "month" not in partitions

    def test_parse_partition_handles_relative_key(self):
        """Test partition parsing with key relative to prefix."""
        asset = S3Asset(
            name="test",
            uri="s3://bucket/base/path/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year"],
        )

        # Key includes the prefix
        key = "base/path/year=2024/data.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"year": "2024"}

    def test_parse_partition_with_empty_prefix(self):
        """Test partition parsing when asset has no prefix."""
        asset = S3Asset(
            name="test",
            uri="s3://bucket/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year"],
        )

        key = "year=2024/data.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"year": "2024"}


class TestS3AssetCreateClient:
    """Test suite for S3Asset._s3_create_client method."""

    def test_create_client_success(self):
        """Test successful S3 client creation."""
        import sys

        mock_boto3 = Mock()
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        sys.modules["boto3"] = mock_boto3

        try:
            asset = S3Asset(
                name="test",
                uri="s3://bucket/data/",
                kind=AssetKind.PARQUET,
                platform=Platform.S3,
                region="us-east-1",
            )

            client = asset._s3_create_client()

            assert client == mock_client
            mock_boto3.client.assert_called_once_with(
                "s3",
                region_name="us-east-1",
            )
        finally:
            # Clean up
            if "boto3" in sys.modules:
                del sys.modules["boto3"]

    def test_create_client_with_no_region(self):
        """Test client creation without region (uses default)."""
        import sys

        mock_boto3 = Mock()
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        sys.modules["boto3"] = mock_boto3

        try:
            asset = S3Asset(
                name="test",
                uri="s3://bucket/data/",
                kind=AssetKind.PARQUET,
                platform=Platform.S3,
            )

            client = asset._s3_create_client()

            assert client == mock_client
            mock_boto3.client.assert_called_once_with(
                "s3",
                region_name=None,
            )
        finally:
            if "boto3" in sys.modules:
                del sys.modules["boto3"]

    def test_create_client_boto3_not_installed(self):
        """Test that ImportError is raised when boto3 is not available."""
        import sys
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "boto3":
                raise ImportError("No module named boto3")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            asset = S3Asset(
                name="test",
                uri="s3://bucket/data/",
                kind=AssetKind.PARQUET,
                platform=Platform.S3,
            )

            with pytest.raises(ImportError, match="boto3 is required for S3Asset") as exc_info:
                asset._s3_create_client()

            # Check exception chaining
            assert exc_info.value.__cause__ is not None

    def test_create_client_boto3_error(self):
        """Test that RuntimeError is raised when boto3 client creation fails."""
        import sys

        mock_boto3 = Mock()
        mock_boto3.client.side_effect = Exception("AWS credentials not found")
        sys.modules["boto3"] = mock_boto3

        try:
            asset = S3Asset(
                name="test",
                uri="s3://bucket/data/",
                kind=AssetKind.PARQUET,
                platform=Platform.S3,
            )

            with pytest.raises(RuntimeError, match="Failed to create S3 client") as exc_info:
                asset._s3_create_client()

            # Check exception chaining
            assert exc_info.value.__cause__ is not None
        finally:
            if "boto3" in sys.modules:
                del sys.modules["boto3"]


class TestS3AssetGetPageIterator:
    """Test suite for S3Asset._s3_get_page_iterator method."""

    def test_get_page_iterator_success(self):
        """Test successful paginator creation."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_page_iterator = Mock()

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_page_iterator

        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/warehouse/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        iterator = asset._s3_get_page_iterator(mock_client)

        assert iterator == mock_page_iterator
        mock_client.get_paginator.assert_called_once_with("list_objects_v2")
        mock_paginator.paginate.assert_called_once_with(
            Bucket="my-bucket",
            Prefix="data/warehouse/",
        )

    def test_get_page_iterator_with_empty_prefix(self):
        """Test paginator with bucket root (empty prefix)."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_page_iterator = Mock()

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_page_iterator

        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        iterator = asset._s3_get_page_iterator(mock_client)

        mock_paginator.paginate.assert_called_once_with(
            Bucket="my-bucket",
            Prefix="",
        )

    def test_get_page_iterator_client_error(self):
        """Test that RuntimeError is raised when paginator creation fails."""
        mock_client = Mock()
        mock_client.get_paginator.side_effect = Exception("Invalid bucket name")

        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        with pytest.raises(RuntimeError, match="Failed to get S3 paginator") as exc_info:
            asset._s3_get_page_iterator(mock_client)

        # Check exception chaining
        assert exc_info.value.__cause__ is not None


# ============================================================================
# S3Asset Tests - Inspect Method
# ============================================================================


class TestS3AssetInspect:
    """Test suite for S3Asset.inspect method."""

    def test_inspect_empty_bucket(self):
        """Test inspect on empty bucket/prefix."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_iterator = [{}]  # Empty page

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="test",
            uri="s3://empty-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        refs = asset.inspect(client=mock_client)

        assert refs == []
        assert asset.domain.refs == []

    def test_inspect_simple_objects(self):
        """Test inspect with simple non-partitioned objects."""
        mock_client = Mock()
        mock_paginator = Mock()

        # Mock S3 response
        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "data/file1.parquet",
                        "Size": 1024,
                        "LastModified": datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
                        "ETag": '"abc123"',
                        "StorageClass": "STANDARD",
                    },
                    {
                        "Key": "data/file2.parquet",
                        "Size": 2048,
                        "LastModified": datetime(2024, 3, 15, 11, 0, 0, tzinfo=timezone.utc),
                        "ETag": '"def456"',
                        "StorageClass": "STANDARD",
                    },
                ]
            }
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="test",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            region="us-west-2",
        )

        refs = asset.inspect(client=mock_client)

        assert len(refs) == 2
        assert all(isinstance(ref, S3AssetRef) for ref in refs)

        # Verify first ref
        assert refs[0].uri == "s3://my-bucket/data/file1.parquet"
        assert refs[0].size == 1024
        assert refs[0].etag == '"abc123"'
        assert refs[0].storage_class == "STANDARD"
        assert refs[0].region == "us-west-2"
        assert refs[0].partitions == {}

        # Verify second ref
        assert refs[1].uri == "s3://my-bucket/data/file2.parquet"
        assert refs[1].size == 2048

    def test_inspect_partitioned_objects(self):
        """Test inspect with partitioned directory structure."""
        mock_client = Mock()
        mock_paginator = Mock()

        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "warehouse/year=2024/month=01/data_01.parquet",
                        "Size": 1024,
                        "LastModified": datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                    },
                    {
                        "Key": "warehouse/year=2024/month=02/data_02.parquet",
                        "Size": 2048,
                        "LastModified": datetime(2024, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
                    },
                    {
                        "Key": "warehouse/year=2023/month=12/data_12.parquet",
                        "Size": 1536,
                        "LastModified": datetime(2023, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
                    },
                ]
            }
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="partitioned",
            uri="s3://data-lake/warehouse/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year", "month"],
        )

        refs = asset.inspect(client=mock_client)

        assert len(refs) == 3

        # Verify partitions are correctly extracted
        assert refs[0].partitions == {"year": "2024", "month": "01"}
        assert refs[1].partitions == {"year": "2024", "month": "02"}
        assert refs[2].partitions == {"year": "2023", "month": "12"}

    def test_inspect_with_pagination(self):
        """Test inspect handles multiple pages correctly."""
        mock_client = Mock()
        mock_paginator = Mock()

        # Mock paginated response (2 pages)
        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "data/file1.parquet",
                        "Size": 1024,
                        "LastModified": datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
                    },
                    {
                        "Key": "data/file2.parquet",
                        "Size": 2048,
                        "LastModified": datetime(2024, 3, 15, 11, 0, 0, tzinfo=timezone.utc),
                    },
                ]
            },
            {
                "Contents": [
                    {
                        "Key": "data/file3.parquet",
                        "Size": 3072,
                        "LastModified": datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
                    },
                ]
            },
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        refs = asset.inspect(client=mock_client)

        # Should collect objects from all pages
        assert len(refs) == 3

    def test_inspect_with_missing_optional_fields(self):
        """Test inspect handles objects with missing optional fields."""
        mock_client = Mock()
        mock_paginator = Mock()

        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "data/file.parquet",
                        "Size": 0,
                        "LastModified": datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
                        # ETag and StorageClass missing
                    },
                ]
            }
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        refs = asset.inspect(client=mock_client)

        assert len(refs) == 1
        assert refs[0].etag is None
        assert refs[0].storage_class is None

    def test_inspect_different_storage_classes(self):
        """Test inspect with various S3 storage classes."""
        mock_client = Mock()
        mock_paginator = Mock()

        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "hot/file1.parquet",
                        "Size": 1024,
                        "LastModified": datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
                        "StorageClass": "STANDARD",
                    },
                    {
                        "Key": "warm/file2.parquet",
                        "Size": 2048,
                        "LastModified": datetime(2024, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
                        "StorageClass": "STANDARD_IA",
                    },
                    {
                        "Key": "cold/file3.parquet",
                        "Size": 3072,
                        "LastModified": datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                        "StorageClass": "GLACIER",
                    },
                    {
                        "Key": "archive/file4.parquet",
                        "Size": 4096,
                        "LastModified": datetime(2023, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
                        "StorageClass": "DEEP_ARCHIVE",
                    },
                ]
            }
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="test",
            uri="s3://bucket/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        refs = asset.inspect(client=mock_client)

        assert len(refs) == 4
        assert refs[0].storage_class == "STANDARD"
        assert refs[1].storage_class == "STANDARD_IA"
        assert refs[2].storage_class == "GLACIER"
        assert refs[3].storage_class == "DEEP_ARCHIVE"

    def test_inspect_updates_domain_refs(self):
        """Test that inspect updates the domain model's refs."""
        mock_client = Mock()
        mock_paginator = Mock()

        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "data/file1.parquet",
                        "Size": 1024,
                        "LastModified": datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
                    },
                ]
            }
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        # Initially no refs
        assert asset.domain.refs == []

        # After inspect, refs should be populated
        refs = asset.inspect(client=mock_client)
        assert asset.domain.refs == refs
        assert len(asset.domain.refs) == 1

    def test_inspect_without_explicit_client(self):
        """Test inspect creates client automatically when not provided."""
        with patch.object(S3Asset, "_s3_create_client") as mock_create:
            with patch.object(S3Asset, "_s3_get_page_iterator") as mock_paginator:
                mock_client = Mock()
                mock_create.return_value = mock_client
                mock_paginator.return_value = iter([{}])

                asset = S3Asset(
                    name="test",
                    uri="s3://bucket/data/",
                    kind=AssetKind.PARQUET,
                    platform=Platform.S3,
                )

                refs = asset.inspect()

                # Should have called _s3_create_client
                mock_create.assert_called_once()
                mock_paginator.assert_called_once_with(mock_client)

    def test_inspect_with_explicit_client(self):
        """Test inspect uses provided client instead of creating new one."""
        mock_client = Mock()
        mock_paginator = Mock()

        mock_iterator = [{}]
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        with patch.object(S3Asset, "_s3_create_client") as mock_create:
            refs = asset.inspect(client=mock_client)

            # Should NOT have called _s3_create_client
            mock_create.assert_not_called()

    def test_inspect_deeply_nested_partitions(self):
        """Test inspect with deeply nested partition structure."""
        mock_client = Mock()
        mock_paginator = Mock()

        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "warehouse/year=2024/month=03/day=15/hour=14/data.parquet",
                        "Size": 1024,
                        "LastModified": datetime(2024, 3, 15, 14, 30, 0, tzinfo=timezone.utc),
                    },
                ]
            }
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="hourly_data",
            uri="s3://data-lake/warehouse/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year", "month", "day", "hour"],
        )

        refs = asset.inspect(client=mock_client)

        assert len(refs) == 1
        assert refs[0].partitions == {
            "year": "2024",
            "month": "03",
            "day": "15",
            "hour": "14",
        }

    def test_inspect_with_size_zero_objects(self):
        """Test inspect handles zero-byte objects (e.g., _SUCCESS markers)."""
        mock_client = Mock()
        mock_paginator = Mock()

        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "data/_SUCCESS",
                        "Size": 0,
                        "LastModified": datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
                    },
                    {
                        "Key": "data/actual_data.parquet",
                        "Size": 1024,
                        "LastModified": datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
                    },
                ]
            }
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        refs = asset.inspect(client=mock_client)

        # Should include both objects
        assert len(refs) == 2
        assert refs[0].size == 0
        assert refs[1].size == 1024


# ============================================================================
# Integration Tests
# ============================================================================


class TestS3AssetIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow_simple(self):
        """Test complete workflow: create asset -> inspect with mocked S3."""
        mock_client = Mock()
        mock_paginator = Mock()

        # Simulate S3 bucket with sales data
        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "sales/2024_q1.parquet",
                        "Size": 5120,
                        "LastModified": datetime(2024, 3, 31, 23, 59, 0, tzinfo=timezone.utc),
                        "ETag": '"sales2024q1"',
                        "StorageClass": "STANDARD",
                    },
                    {
                        "Key": "sales/2023_q4.parquet",
                        "Size": 4096,
                        "LastModified": datetime(2023, 12, 31, 23, 59, 0, tzinfo=timezone.utc),
                        "ETag": '"sales2023q4"',
                        "StorageClass": "STANDARD_IA",
                    },
                ]
            }
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        # Create asset
        asset = S3Asset(
            name="quarterly_sales",
            uri="s3://company-data-lake/sales/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            region="us-east-1",
            description="Quarterly sales aggregations",
            owner="analytics_team",
        )

        # Inspect
        refs = asset.inspect(client=mock_client)

        assert len(refs) == 2
        assert asset.domain.description == "Quarterly sales aggregations"
        assert all(ref.region == "us-east-1" for ref in refs)

        # Verify domain is updated
        assert len(asset.domain.refs) == 2

    def test_full_workflow_partitioned(self):
        """Test workflow with partitioned data across multiple months."""
        mock_client = Mock()
        mock_paginator = Mock()

        # Simulate partitioned structure
        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "warehouse/transactions/year=2024/month=01/part-00000.parquet",
                        "Size": 2048,
                        "LastModified": datetime(2024, 1, 31, 10, 0, 0, tzinfo=timezone.utc),
                    },
                    {
                        "Key": "warehouse/transactions/year=2024/month=01/part-00001.parquet",
                        "Size": 2048,
                        "LastModified": datetime(2024, 1, 31, 10, 5, 0, tzinfo=timezone.utc),
                    },
                    {
                        "Key": "warehouse/transactions/year=2024/month=02/part-00000.parquet",
                        "Size": 3072,
                        "LastModified": datetime(2024, 2, 29, 10, 0, 0, tzinfo=timezone.utc),
                    },
                ]
            }
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="transactions",
            uri="s3://data-warehouse/warehouse/transactions/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["year", "month"],
            tags={"source": "production", "frequency": "daily"},
        )

        refs = asset.inspect(client=mock_client)

        assert len(refs) == 3

        # Verify partitions
        month_01_refs = [r for r in refs if r.partitions["month"] == "01"]
        month_02_refs = [r for r in refs if r.partitions["month"] == "02"]

        assert len(month_01_refs) == 2
        assert len(month_02_refs) == 1

        # Verify all have year=2024
        assert all(ref.partitions["year"] == "2024" for ref in refs)

    def test_error_handling_in_workflow(self):
        """Test that errors during inspect are properly raised."""
        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        # Mock client that raises error during pagination
        mock_client = Mock()
        mock_client.get_paginator.side_effect = Exception("Access Denied")

        with pytest.raises(RuntimeError, match="Failed to get S3 paginator"):
            asset.inspect(client=mock_client)

    def test_large_bucket_performance(self):
        """Smoke test: inspect handles large number of objects efficiently."""
        mock_client = Mock()
        mock_paginator = Mock()

        # Simulate 10 pages with 100 objects each (1000 total objects)
        pages = []
        for page_num in range(10):
            contents = []
            for obj_num in range(100):
                contents.append(
                    {
                        "Key": f"data/partition={page_num}/file_{obj_num}.parquet",
                        "Size": 1024 * obj_num,
                        "LastModified": datetime(
                            2024, 3, 15, page_num, obj_num % 60, 0, tzinfo=timezone.utc
                        ),
                    }
                )
            pages.append({"Contents": contents})

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = pages

        asset = S3Asset(
            name="large_dataset",
            uri="s3://big-bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["partition"],
        )

        refs = asset.inspect(client=mock_client)

        # Should handle 1000 objects
        assert len(refs) == 1000

        # Verify partitions are extracted
        unique_partitions = {ref.partitions["partition"] for ref in refs}
        assert len(unique_partitions) == 10  # 10 different partitions


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestS3AssetEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_asset_with_special_characters_in_prefix(self):
        """Test asset with spaces and special characters in prefix."""
        asset = S3Asset(
            name="special",
            uri="s3://bucket/path with spaces/data-2024/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        assert asset.domain.prefix == "path with spaces/data-2024/"

    def test_asset_with_trailing_slash_variations(self):
        """Test that trailing slash is handled consistently."""
        asset_with_slash = S3Asset(
            name="test1",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        asset_without_slash = S3Asset(
            name="test2",
            uri="s3://bucket/data",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        # Both should work, prefix behavior determined by urlparse
        assert asset_with_slash.domain.prefix == "data/"
        assert asset_without_slash.domain.prefix == "data"

    def test_inspect_handles_contents_key_missing(self):
        """Test inspect gracefully handles pages without Contents key."""
        mock_client = Mock()
        mock_paginator = Mock()

        # Page without Contents key (no matching objects)
        mock_iterator = [
            {"IsTruncated": False},
        ]

        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = mock_iterator

        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
        )

        refs = asset.inspect(client=mock_client)
        assert refs == []

    def test_partition_key_with_equals_in_value(self):
        """Test partition parsing when value contains equals sign."""
        asset = S3Asset(
            name="test",
            uri="s3://bucket/data/",
            kind=AssetKind.PARQUET,
            platform=Platform.S3,
            partitions=["query"],
        )

        # Key with equals in the value
        key = "data/query=key=value/file.parquet"
        partitions = asset._parse_partition(key)

        # Should split only on first =, so value keeps remaining equals
        assert partitions == {"query": "key=value"}

    def test_model_export_and_recreation(self):
        """Test that model can be exported and recreated."""
        original = S3AssetModel(
            name="test_asset",
            uri="s3://my-bucket/data/",
            kind=AssetKind.PARQUET,
            region="eu-west-1",
            partitions=["year", "month"],
            description="Test description",
            tags={"env": "test"},
        )

        # Export to dict
        exported = original.model_dump()

        # Recreate from dict
        recreated = S3AssetModel(**exported)

        assert recreated.name == original.name
        assert recreated.uri == original.uri
        assert recreated.region == original.region
        assert recreated.partitions == original.partitions
        assert recreated.bucket == original.bucket
        assert recreated.prefix == original.prefix
