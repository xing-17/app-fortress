"""
Unit tests for OSSAsset, OSSAssetModel, and OSSAssetRef classes.

Tests cover:
- OSSAssetRef: URI parsing, bucket/prefix extraction
- OSSAssetModel: Domain model validation
- OSSAsset: Partition extraction, object inspection
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from bastion.control.asset.oss.oss import OSSAsset, OSSAssetModel, OSSAssetRef
from bastion.control.asset.oss.adaptor import IOSSAdaptorLike
from bastion.domain.assetkind import AssetKind
from bastion.domain.platform import Platform

import warnings

warnings.filterwarnings("ignore")
pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ============================================================================
# OSSAssetRef Tests
# ============================================================================


class TestOSSAssetRef:
    """Test suite for OSSAssetRef class."""

    def test_bucket_computed_field(self):
        """Test that bucket is correctly extracted from URI."""
        ref = OSSAssetRef(
            uri="oss://my-bucket/path/to/file.parquet",
            partitions={},
            size=1024,
        )
        assert ref.bucket == "my-bucket"

    def test_prefix_computed_field(self):
        """Test that prefix is correctly extracted from URI."""
        ref = OSSAssetRef(
            uri="oss://my-bucket/path/to/file.parquet",
            partitions={},
            size=1024,
        )
        assert ref.prefix == "path/to/file.parquet"

    def test_ref_with_region(self):
        """Test OSSAssetRef with region metadata."""
        ref = OSSAssetRef(
            uri="oss://my-bucket/data/file.parquet",
            partitions={},
            size=2048,
            region="oss-cn-hangzhou",
        )
        assert ref.region == "oss-cn-hangzhou"
        assert ref.bucket == "my-bucket"
        assert ref.prefix == "data/file.parquet"

    def test_ref_with_partitions(self):
        """Test OSSAssetRef with partition metadata."""
        ref = OSSAssetRef(
            uri="oss://bucket/year=2024/month=01/data.parquet",
            partitions={"year": "2024", "month": "01"},
            size=4096,
        )
        assert ref.partitions == {"year": "2024", "month": "01"}

    def test_ref_with_metadata(self):
        """Test OSSAssetRef with all metadata fields."""
        modified = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        ref = OSSAssetRef(
            uri="oss://bucket/file.parquet",
            partitions={},
            size=8192,
            modified_at=modified,
            region="oss-cn-beijing",
        )

        assert ref.size == 8192
        assert ref.modified_at == modified
        assert ref.region == "oss-cn-beijing"

    def test_parse_invalid_uri(self):
        """Test that invalid URI raises ValueError."""
        with pytest.raises(ValueError, match="Invalid OSS URI"):
            ref = OSSAssetRef(
                uri="s3://bucket/file.parquet",
                partitions={},
                size=1024,
            )
            _ = ref.bucket


# ============================================================================
# OSSAssetModel Tests
# ============================================================================


class TestOSSAssetModel:
    """Test suite for OSSAssetModel domain model."""

    def test_model_creation_with_required_fields(self):
        """Test creating a model with all required fields."""
        model = OSSAssetModel(
            name="test_asset",
            uri="oss://my-bucket/path/to/data",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
        )

        assert model.name == "test_asset"
        assert model.uri == "oss://my-bucket/path/to/data"
        assert model.region == "oss-cn-hangzhou"
        assert model.kind == AssetKind.PARQUET
        assert model.platform == Platform.OSS

    def test_model_platform_defaults_to_oss(self):
        """Test that platform defaults to OSS."""
        model = OSSAssetModel(
            name="sales",
            uri="oss://bucket/sales",
            region="oss-cn-shanghai",
            kind=AssetKind.CSV,
        )
        assert model.platform == Platform.OSS

    def test_model_bucket_computed_field(self):
        """Test that bucket is computed from URI."""
        model = OSSAssetModel(
            name="test",
            uri="oss://test-bucket/data/path",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
        )
        assert model.bucket == "test-bucket"

    def test_model_prefix_computed_field(self):
        """Test that prefix is computed from URI."""
        model = OSSAssetModel(
            name="test",
            uri="oss://test-bucket/data/path",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
        )
        assert model.prefix == "data/path"

    def test_model_with_endpoint(self):
        """Test model with custom endpoint."""
        model = OSSAssetModel(
            name="custom",
            uri="oss://bucket/data",
            region="oss-cn-hangzhou",
            endpoint="oss-cn-hangzhou.aliyuncs.com",
            kind=AssetKind.PARQUET,
        )
        assert model.endpoint == "oss-cn-hangzhou.aliyuncs.com"

    def test_model_with_partitions(self):
        """Test model with partition columns."""
        model = OSSAssetModel(
            name="partitioned_data",
            uri="oss://bucket/warehouse",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
            partitions=["year", "month", "day"],
        )
        assert model.partitions == ["year", "month", "day"]

    def test_model_with_metadata(self):
        """Test model with optional metadata fields."""
        model = OSSAssetModel(
            name="enriched_asset",
            uri="oss://bucket/data",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
            description="Test asset with metadata",
            owner="data_team",
            tags={"env": "test", "category": "demo"},
        )

        assert model.description == "Test asset with metadata"
        assert model.owner == "data_team"
        assert model.tags == {"env": "test", "category": "demo"}


# ============================================================================
# OSSAsset Tests
# ============================================================================


class TestOSSAssetParsePartition:
    """Test suite for OSSAsset._parse_partition method."""

    def test_parse_partition_no_partitions(self):
        """Test parsing when no partitions are defined."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data/file.parquet",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
        )

        result = asset._parse_partition("data/file.parquet")
        assert result == {}

    def test_parse_partition_with_partitions(self):
        """Test parsing partition values from key."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
            partitions=["year", "month"],
        )

        result = asset._parse_partition("data/year=2024/month=01/file.parquet")
        assert result == {"year": "2024", "month": "01"}

    def test_parse_partition_with_extra_columns(self):
        """Test that only defined partitions are extracted."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
            partitions=["year"],
        )

        result = asset._parse_partition("data/year=2024/month=01/file.parquet")
        assert result == {"year": "2024"}

    def test_parse_partition_missing_equals(self):
        """Test that non-partition path parts are ignored."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
            partitions=["year"],
        )

        result = asset._parse_partition("data/year=2024/subdir/file.parquet")
        assert result == {"year": "2024"}


class TestOSSAssetInspect:
    """Test suite for OSSAsset.inspect method."""

    def test_inspect_with_mock_adaptor(self):
        """Test inspect with a mocked adaptor."""
        # Create mock adaptor
        mock_adaptor = Mock(spec=IOSSAdaptorLike)
        
        # Create mock OSS objects
        mock_obj = Mock()
        mock_obj.key = "data/file.parquet"
        mock_obj.size = 1024
        mock_dt = Mock()
        mock_dt.astimezone.return_value = datetime(2024, 1, 15, tzinfo=UTC)
        mock_obj.last_modified = mock_dt
        
        mock_adaptor.list_objects.return_value = [mock_obj]

        # Create asset
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
        )

        # Inspect
        refs = asset.inspect(adaptor=mock_adaptor)

        # Assertions
        assert len(refs) == 1
        assert refs[0].uri == "oss://bucket/data/file.parquet"
        assert refs[0].size == 1024
        assert refs[0].bucket == "bucket"
        assert refs[0].prefix == "data/file.parquet"

    def test_inspect_with_partitioned_data(self):
        """Test inspect with partitioned data."""
        # Create mock adaptor
        mock_adaptor = Mock(spec=IOSSAdaptorLike)
        
        # Create mock OSS objects
        mock_obj = Mock()
        mock_obj.key = "data/year=2024/month=01/file.parquet"
        mock_obj.size = 2048
        mock_dt = Mock()
        mock_dt.astimezone.return_value = datetime(2024, 1, 15, tzinfo=UTC)
        mock_obj.last_modified = mock_dt
        
        mock_adaptor.list_objects.return_value = [mock_obj]

        # Create asset with partitions
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
            partitions=["year", "month"],
        )

        # Inspect
        refs = asset.inspect(adaptor=mock_adaptor)

        # Assertions
        assert len(refs) == 1
        assert refs[0].partitions == {"year": "2024", "month": "01"}

    def test_inspect_stores_refs_in_domain(self):
        """Test that inspect stores refs in the domain model."""
        # Create mock adaptor
        mock_adaptor = Mock(spec=IOSSAdaptorLike)
        mock_adaptor.list_objects.return_value = []

        # Create asset
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data",
            region="oss-cn-hangzhou",
            kind=AssetKind.PARQUET,
        )

        # Inspect
        refs = asset.inspect(adaptor=mock_adaptor)

        # Assertions
        assert asset.domain.refs == refs
        assert len(refs) == 0
