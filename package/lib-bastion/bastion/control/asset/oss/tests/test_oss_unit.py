"""
Comprehensive unit tests for OSSAsset, OSSAssetModel, and OSSAssetRef classes.

Tests cover:
- OSSAssetRef: URI parsing, bucket/prefix extraction, metadata fields
- OSSAssetModel: Domain model validation, computed fields
- OSSAsset: Client creation, pagination, partition extraction, inspection
- Error handling: Invalid URIs, OSS errors, pagination failures
- Edge cases: Empty buckets, large result sets, special characters
- Integration: Complete workflows with mocked Alibaba Cloud OSS responses
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from bastion.control.asset.oss.oss import (
    OSSAsset,
    OSSAssetModel,
    OSSAssetRef,
)
from bastion.domain.assetkind import AssetKind
from bastion.domain.platform import Platform

# ============================================================================
# OSSAssetRef Tests
# ============================================================================


class TestOSSAssetRef:
    """Test suite for OSSAssetRef class."""

    def test_bucket_computed_field(self):
        """Test that bucket returns the bucket name from oss:// URI."""
        ref = OSSAssetRef(
            uri="oss://my-bucket/path/to/object.parquet",
            partitions={},
            size=1024,
        )
        assert ref.bucket == "my-bucket"

    def test_prefix_computed_field(self):
        """Test that prefix returns the key path without leading slash."""
        ref = OSSAssetRef(
            uri="oss://my-bucket/path/to/object.parquet",
            partitions={},
            size=1024,
        )
        assert ref.prefix == "path/to/object.parquet"

    def test_bucket_and_prefix_with_nested_path(self):
        """Test bucket and prefix extraction from deeply nested path."""
        ref = OSSAssetRef(
            uri="oss://data-warehouse/year=2024/month=03/day=15/data.parquet",
            partitions={"year": "2024", "month": "03", "day": "15"},
            size=4096,
        )
        assert ref.bucket == "data-warehouse"
        assert ref.prefix == "year=2024/month=03/day=15/data.parquet"

    def test_invalid_uri_scheme_raises_error(self):
        """Test that non-OSS URI schemes raise ValueError."""
        with pytest.raises(ValueError, match="Invalid OSS URI"):
            OSSAssetRef(
                uri="http://example.com/data.parquet",
                partitions={},
                size=1024,
            ).bucket

    def test_invalid_uri_scheme_in_prefix_raises_error(self):
        """Test that non-OSS URI schemes raise ValueError for prefix."""
        with pytest.raises(ValueError, match="Invalid OSS URI"):
            OSSAssetRef(
                uri="file:///local/path/data.parquet",
                partitions={},
                size=1024,
            ).prefix

    def test_ref_with_all_metadata(self):
        """Test OSSAssetRef with all optional fields."""
        modified = datetime(2024, 3, 15, 10, 30, 0, tzinfo=UTC)

        ref = OSSAssetRef(
            uri="oss://my-bucket/data/file.parquet",
            partitions={"year": "2024"},
            size=8192,
            modified_at=modified,
            region="oss-cn-hangzhou",
        )

        assert ref.size == 8192
        assert ref.modified_at == modified
        assert ref.region == "oss-cn-hangzhou"
        assert ref.partitions == {"year": "2024"}

    def test_ref_without_optional_fields(self):
        """Test OSSAssetRef with minimal required fields."""
        ref = OSSAssetRef(
            uri="oss://bucket/key",
            partitions={},
            size=0,
        )
        assert ref.region is None
        assert ref.modified_at is None

    def test_prefix_strips_leading_slash(self):
        """Test that prefix removes leading slash if present."""
        ref = OSSAssetRef(
            uri="oss://bucket//path/with/double/slash.parquet",
            partitions={},
            size=1024,
        )
        # urlparse should handle this, but prefix strips leading /
        assert not ref.prefix.startswith("/")

    def test_bucket_with_hyphens(self):
        """Test bucket names with hyphens."""
        ref = OSSAssetRef(
            uri="oss://my-bucket-name-123/data/file.parquet",
            partitions={},
            size=1024,
        )
        assert ref.bucket == "my-bucket-name-123"

    def test_bucket_with_chinese_characters_in_path(self):
        """Test handling of Chinese characters in object path."""
        ref = OSSAssetRef(
            uri="oss://my-bucket/数据/文件.parquet",
            partitions={},
            size=1024,
        )
        assert ref.bucket == "my-bucket"
        assert ref.prefix == "数据/文件.parquet"


# ============================================================================
# OSSAssetModel Tests
# ============================================================================


class TestOSSAssetModel:
    """Test suite for OSSAssetModel domain model."""

    def test_model_creation_with_required_fields(self):
        """Test creating a model with all required fields."""
        model = OSSAssetModel(
            name="test_asset",
            uri="oss://my-bucket/data/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
        )

        assert model.name == "test_asset"
        assert model.uri == "oss://my-bucket/data/"
        assert model.kind == AssetKind.PARQUET
        assert model.platform == Platform.OSS
        assert model.region == "oss-cn-hangzhou"

    def test_model_platform_defaults_to_oss(self):
        """Test that platform is set to OSS."""
        model = OSSAssetModel(
            name="sales",
            uri="oss://data-lake/sales/",
            kind=AssetKind.CSV,
            region="oss-cn-beijing",
        )
        assert model.platform == Platform.OSS

    def test_model_bucket_computed_field(self):
        """Test that bucket is computed from URI."""
        model = OSSAssetModel(
            name="test",
            uri="oss://my-bucket/prefix/path/",
            kind=AssetKind.PARQUET,
            region="oss-cn-shanghai",
        )
        assert model.bucket == "my-bucket"

    def test_model_prefix_computed_field(self):
        """Test that prefix is computed from URI."""
        model = OSSAssetModel(
            name="test",
            uri="oss://my-bucket/data/warehouse/sales/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
        )
        assert model.prefix == "data/warehouse/sales/"

    def test_model_with_endpoint(self):
        """Test model with custom OSS endpoint."""
        model = OSSAssetModel(
            name="custom_endpoint",
            uri="oss://my-bucket/data/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
            endpoint="oss-cn-hangzhou.aliyuncs.com",
        )
        assert model.endpoint == "oss-cn-hangzhou.aliyuncs.com"

    def test_model_with_partitions(self):
        """Test model with partition columns."""
        model = OSSAssetModel(
            name="partitioned_data",
            uri="oss://warehouse/tables/sales/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
            partitions=["year", "month", "day"],
        )
        assert model.partitions == ["year", "month", "day"]

    def test_model_with_metadata(self):
        """Test model with optional metadata fields."""
        model = OSSAssetModel(
            name="enriched_asset",
            uri="oss://data-lake/enriched/",
            kind=AssetKind.PARQUET,
            region="oss-cn-shanghai",
            description="Test OSS asset with metadata",
            owner="data_team",
            tags={"env": "prod", "category": "analytics"},
        )

        assert model.description == "Test OSS asset with metadata"
        assert model.owner == "data_team"
        assert model.tags == {"env": "prod", "category": "analytics"}

    def test_model_with_refs(self):
        """Test model with file references."""
        ref = OSSAssetRef(
            uri="oss://bucket/data/file.parquet",
            partitions={},
            size=1024,
        )

        model = OSSAssetModel(
            name="asset_with_refs",
            uri="oss://bucket/data/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
            refs=[ref],
        )

        assert len(model.refs) == 1
        assert model.refs[0].uri == "oss://bucket/data/file.parquet"

    def test_model_invalid_uri_scheme_raises_error(self):
        """Test that invalid URI scheme raises error when accessing bucket."""
        model = OSSAssetModel(
            name="invalid",
            uri="https://bucket.oss-cn-hangzhou.aliyuncs.com/data/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
        )

        with pytest.raises(ValueError, match="Invalid OSS URI"):
            _ = model.bucket

    def test_model_empty_prefix(self):
        """Test model with bucket root (empty prefix)."""
        model = OSSAssetModel(
            name="root_data",
            uri="oss://my-bucket/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
        )
        assert model.bucket == "my-bucket"
        assert model.prefix == ""

    def test_model_with_different_regions(self):
        """Test model with various OSS regions."""
        regions = [
            "oss-cn-hangzhou",
            "oss-cn-shanghai",
            "oss-cn-beijing",
            "oss-cn-shenzhen",
            "oss-ap-southeast-1",
        ]

        for region in regions:
            model = OSSAssetModel(
                name=f"test_{region}",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region=region,
            )
            assert model.region == region


# ============================================================================
# OSSAsset Tests - Helper Methods
# ============================================================================


class TestOSSAssetParsePartition:
    """Test suite for OSSAsset._parse_partition method."""

    def test_parse_single_partition(self):
        """Test extracting a single partition value from OSS key."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
            partitions=["year"],
        )

        key = "data/year=2024/file.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"year": "2024"}

    def test_parse_multiple_partitions(self):
        """Test extracting multiple partition values."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/warehouse/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
            partitions=["year", "month", "day"],
        )

        key = "warehouse/year=2024/month=03/day=15/data.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"year": "2024", "month": "03", "day": "15"}

    def test_parse_partition_with_no_partitions(self):
        """Test that non-partitioned assets return empty dict."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data/",
            kind=AssetKind.CSV,
            region="oss-cn-hangzhou",
        )

        key = "data/file.csv"
        partitions = asset._parse_partition(key)

        assert partitions == {}

    def test_parse_partition_ignores_non_partition_dirs(self):
        """Test that non-partition directories are ignored."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/warehouse/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
            partitions=["year", "month"],
        )

        key = "warehouse/other/year=2024/month=06/file.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"year": "2024", "month": "06"}
        assert "other" not in partitions

    def test_parse_partition_with_special_characters(self):
        """Test partition extraction with special characters in values."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
            partitions=["region", "category"],
        )

        key = "data/region=cn-east-1/category=tech_hardware/data.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"region": "cn-east-1", "category": "tech_hardware"}

    def test_parse_partition_only_extracts_defined_partitions(self):
        """Test that only defined partition columns are extracted."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/data/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
            partitions=["year"],
        )

        key = "data/year=2024/month=03/file.parquet"
        partitions = asset._parse_partition(key)

        # Should only extract 'year', not 'month'
        assert partitions == {"year": "2024"}
        assert "month" not in partitions

    def test_parse_partition_handles_relative_key(self):
        """Test partition parsing with key relative to prefix."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/base/path/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
            partitions=["year"],
        )

        # Key includes the prefix
        key = "base/path/year=2024/data.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"year": "2024"}

    def test_parse_partition_with_empty_prefix(self):
        """Test partition parsing when asset has no prefix."""
        asset = OSSAsset(
            name="test",
            uri="oss://bucket/",
            kind=AssetKind.PARQUET,
            region="oss-cn-hangzhou",
            partitions=["year"],
        )

        key = "year=2024/data.parquet"
        partitions = asset._parse_partition(key)

        assert partitions == {"year": "2024"}


# ============================================================================
# OSSAsset Tests - Client Creation
# ============================================================================


class TestOSSAssetCreateClient:
    """Test suite for OSSAsset._oss_create_client method."""

    def test_create_client_success(self):
        """Test successful OSS client creation."""
        import sys

        # Mock the alibabacloud_oss_v2 module
        mock_ossv2 = Mock()
        mock_credentials = Mock()
        mock_config = Mock()
        mock_client = Mock()

        mock_ossv2.credentials.EnvironmentVariableCredentialsProvider.return_value = (
            mock_credentials
        )
        mock_ossv2.config.load_default.return_value = mock_config
        mock_ossv2.Client.return_value = mock_client

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2
        sys.modules["alibabacloud_oss_v2.credentials"] = mock_ossv2.credentials
        sys.modules["alibabacloud_oss_v2.config"] = mock_ossv2.config

        try:
            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            client = asset._oss_create_client()

            assert client == mock_client
            assert mock_config.region == "oss-cn-hangzhou"
            assert mock_config.credentials_provider == mock_credentials
            mock_ossv2.Client.assert_called_once_with(mock_config)
        finally:
            # Clean up
            for module in [
                "alibabacloud_oss_v2",
                "alibabacloud_oss_v2.credentials",
                "alibabacloud_oss_v2.config",
            ]:
                if module in sys.modules:
                    del sys.modules[module]

    def test_create_client_with_custom_endpoint(self):
        """Test client creation with custom endpoint."""
        import sys

        mock_ossv2 = Mock()
        mock_credentials = Mock()
        mock_config = Mock()
        mock_client = Mock()

        mock_ossv2.credentials.EnvironmentVariableCredentialsProvider.return_value = (
            mock_credentials
        )
        mock_ossv2.config.load_default.return_value = mock_config
        mock_ossv2.Client.return_value = mock_client

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2
        sys.modules["alibabacloud_oss_v2.credentials"] = mock_ossv2.credentials
        sys.modules["alibabacloud_oss_v2.config"] = mock_ossv2.config

        try:
            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
                endpoint="oss-cn-hangzhou-internal.aliyuncs.com",
            )

            client = asset._oss_create_client()

            assert client == mock_client
            assert mock_config.region == "oss-cn-hangzhou"
            assert mock_config.endpoint == "oss-cn-hangzhou-internal.aliyuncs.com"
        finally:
            for module in [
                "alibabacloud_oss_v2",
                "alibabacloud_oss_v2.credentials",
                "alibabacloud_oss_v2.config",
            ]:
                if module in sys.modules:
                    del sys.modules[module]

    def test_create_client_ossv2_not_installed(self):
        """Test that ImportError is raised when alibabacloud_oss_v2 is not available."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "alibabacloud_oss_v2":
                raise ImportError("No module named alibabacloud_oss_v2")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            with pytest.raises(
                ImportError, match="alibabacloud_oss_v2 is required for OSSAsset"
            ) as exc_info:
                asset._oss_create_client()

            # Check exception chaining
            assert exc_info.value.__cause__ is not None

    def test_create_client_ossv2_error(self):
        """Test that RuntimeError is raised when OSS client creation fails."""
        import sys

        mock_ossv2 = Mock()
        mock_ossv2.credentials.EnvironmentVariableCredentialsProvider.side_effect = Exception(
            "OSS credentials not found"
        )

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2
        sys.modules["alibabacloud_oss_v2.credentials"] = mock_ossv2.credentials

        try:
            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            with pytest.raises(
                RuntimeError, match="Failed to create OSS bucket client"
            ) as exc_info:
                asset._oss_create_client()

            # Check exception chaining
            assert exc_info.value.__cause__ is not None
        finally:
            for module in ["alibabacloud_oss_v2", "alibabacloud_oss_v2.credentials"]:
                if module in sys.modules:
                    del sys.modules[module]


# ============================================================================
# OSSAsset Tests - Paginator
# ============================================================================


class TestOSSAssetGetObjectPaginator:
    """Test suite for OSSAsset._oss_get_object_paginator method."""

    def test_get_paginator_success(self):
        """Test successful paginator creation."""
        import sys

        mock_ossv2 = Mock()
        mock_client = Mock()
        mock_paginator = Mock()

        mock_client.list_objects_v2_paginator.return_value = mock_paginator

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            asset = OSSAsset(
                name="test",
                uri="oss://my-bucket/data/warehouse/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            paginator = asset._oss_get_object_paginator(mock_client)

            assert paginator == mock_paginator
            mock_client.list_objects_v2_paginator.assert_called_once()
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]

    def test_get_paginator_client_error(self):
        """Test that RuntimeError is raised when paginator creation fails."""
        import sys

        mock_ossv2 = Mock()
        mock_client = Mock()
        mock_client.list_objects_v2_paginator.side_effect = Exception("Invalid bucket name")

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            with pytest.raises(
                RuntimeError, match="Failed to create OSS object paginator"
            ) as exc_info:
                asset._oss_get_object_paginator(mock_client)

            assert exc_info.value.__cause__ is not None
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]


# ============================================================================
# OSSAsset Tests - Build Request
# ============================================================================


class TestOSSAssetBuildRequest:
    """Test suite for OSSAsset._oss_build_request method."""

    def test_build_request_success(self):
        """Test successful request building."""
        import sys

        mock_ossv2 = Mock()
        mock_request = Mock()
        mock_ossv2.ListObjectsV2Request.return_value = mock_request

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            asset = OSSAsset(
                name="test",
                uri="oss://my-bucket/data/warehouse/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            request = asset._oss_build_request()

            assert request == mock_request
            mock_ossv2.ListObjectsV2Request.assert_called_once_with(
                bucket="my-bucket",
                prefix="data/warehouse/",
            )
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]

    def test_build_request_with_empty_prefix(self):
        """Test request building with bucket root (empty prefix)."""
        import sys

        mock_ossv2 = Mock()
        mock_request = Mock()
        mock_ossv2.ListObjectsV2Request.return_value = mock_request

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            asset = OSSAsset(
                name="test",
                uri="oss://my-bucket/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            _ = asset._oss_build_request()

            mock_ossv2.ListObjectsV2Request.assert_called_once_with(
                bucket="my-bucket",
                prefix="",
            )
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]

    def test_build_request_ossv2_not_installed(self):
        """Test that ImportError is raised when alibabacloud_oss_v2 is not available."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "alibabacloud_oss_v2":
                raise ImportError("No module named alibabacloud_oss_v2")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            with pytest.raises(
                ImportError, match="alibabacloud_oss_v2 is required for OSSAsset"
            ) as exc_info:
                asset._oss_build_request()

            assert exc_info.value.__cause__ is not None

    def test_build_request_error(self):
        """Test that RuntimeError is raised when request building fails."""
        import sys

        mock_ossv2 = Mock()
        mock_ossv2.ListObjectsV2Request.side_effect = Exception("Invalid parameters")

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            with pytest.raises(RuntimeError, match="Failed to build OSS request") as exc_info:
                asset._oss_build_request()

            assert exc_info.value.__cause__ is not None
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]


# ============================================================================
# OSSAsset Tests - Inspect Method
# ============================================================================


class TestOSSAssetInspect:
    """Test suite for OSSAsset.inspect method."""

    def test_inspect_empty_bucket(self):
        """Test inspect on empty bucket/prefix."""
        import sys

        mock_ossv2 = Mock()
        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_iterator = iter([Mock(contents=[])])  # Empty page

            mock_client.list_objects_v2_paginator.return_value = mock_paginator
            mock_paginator.iter_page.return_value = mock_iterator

            asset = OSSAsset(
                name="test",
                uri="oss://empty-bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            refs = asset.inspect(client=mock_client)

            assert refs == []
            assert asset.domain.refs == []
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]

    def test_inspect_simple_objects(self):
        """Test inspect with simple non-partitioned objects."""
        import sys

        mock_ossv2 = Mock()
        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            mock_client = Mock()
            mock_paginator = Mock()

            # Mock OSS response
            obj1 = Mock()
            obj1.key = "data/file1.parquet"
            obj1.size = 1024
            obj1.last_modified = datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC)

            obj2 = Mock()
            obj2.key = "data/file2.parquet"
            obj2.size = 2048
            obj2.last_modified = datetime(2024, 3, 15, 11, 0, 0, tzinfo=UTC)

            page = Mock()
            page.contents = [obj1, obj2]

            mock_iterator = iter([page])

            mock_client.list_objects_v2_paginator.return_value = mock_paginator
            mock_paginator.iter_page.return_value = mock_iterator

            asset = OSSAsset(
                name="test",
                uri="oss://my-bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            refs = asset.inspect(client=mock_client)

            assert len(refs) == 2
            assert all(isinstance(ref, OSSAssetRef) for ref in refs)

            # Verify first ref
            assert refs[0].uri == "oss://my-bucket/data/file1.parquet"
            assert refs[0].size == 1024
            assert refs[0].region == "oss-cn-hangzhou"
            assert refs[0].partitions == {}

            # Verify second ref
            assert refs[1].uri == "oss://my-bucket/data/file2.parquet"
            assert refs[1].size == 2048
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]

    def test_inspect_partitioned_objects(self):
        """Test inspect with partitioned directory structure."""
        import sys

        mock_ossv2 = Mock()
        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            mock_client = Mock()
            mock_paginator = Mock()

            obj1 = Mock()
            obj1.key = "warehouse/year=2024/month=01/data_01.parquet"
            obj1.size = 1024
            obj1.last_modified = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

            obj2 = Mock()
            obj2.key = "warehouse/year=2024/month=02/data_02.parquet"
            obj2.size = 2048
            obj2.last_modified = datetime(2024, 2, 15, 10, 0, 0, tzinfo=UTC)

            obj3 = Mock()
            obj3.key = "warehouse/year=2023/month=12/data_12.parquet"
            obj3.size = 1536
            obj3.last_modified = datetime(2023, 12, 15, 10, 0, 0, tzinfo=UTC)

            page = Mock()
            page.contents = [obj1, obj2, obj3]

            mock_iterator = iter([page])

            mock_client.list_objects_v2_paginator.return_value = mock_paginator
            mock_paginator.iter_page.return_value = mock_iterator

            asset = OSSAsset(
                name="partitioned",
                uri="oss://data-lake/warehouse/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
                partitions=["year", "month"],
            )

            refs = asset.inspect(client=mock_client)

            assert len(refs) == 3

            # Verify partitions are correctly extracted
            assert refs[0].partitions == {"year": "2024", "month": "01"}
            assert refs[1].partitions == {"year": "2024", "month": "02"}
            assert refs[2].partitions == {"year": "2023", "month": "12"}
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]

    def test_inspect_with_pagination(self):
        """Test inspect handles multiple pages correctly."""
        import sys

        mock_ossv2 = Mock()
        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            mock_client = Mock()
            mock_paginator = Mock()

            # Mock paginated response (2 pages)
            obj1 = Mock()
            obj1.key = "data/file1.parquet"
            obj1.size = 1024
            obj1.last_modified = datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC)

            obj2 = Mock()
            obj2.key = "data/file2.parquet"
            obj2.size = 2048
            obj2.last_modified = datetime(2024, 3, 15, 11, 0, 0, tzinfo=UTC)

            obj3 = Mock()
            obj3.key = "data/file3.parquet"
            obj3.size = 3072
            obj3.last_modified = datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC)

            page1 = Mock()
            page1.contents = [obj1, obj2]

            page2 = Mock()
            page2.contents = [obj3]

            mock_iterator = iter([page1, page2])

            mock_client.list_objects_v2_paginator.return_value = mock_paginator
            mock_paginator.iter_page.return_value = mock_iterator

            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            refs = asset.inspect(client=mock_client)

            # Should collect objects from all pages
            assert len(refs) == 3
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]

    def test_inspect_updates_domain_refs(self):
        """Test that inspect updates the domain model's refs."""
        import sys

        mock_ossv2 = Mock()
        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            mock_client = Mock()
            mock_paginator = Mock()

            obj = Mock()
            obj.key = "data/file.parquet"
            obj.size = 1024
            obj.last_modified = datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC)

            page = Mock()
            page.contents = [obj]

            mock_iterator = iter([page])

            mock_client.list_objects_v2_paginator.return_value = mock_paginator
            mock_paginator.iter_page.return_value = mock_iterator

            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            refs = asset.inspect(client=mock_client)

            # Verify domain refs are updated
            assert asset.domain.refs == refs
            assert len(asset.domain.refs) == 1
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]

    def test_inspect_without_client(self):
        """Test inspect creates its own client when not provided."""
        import sys

        # Mock the alibabacloud_oss_v2 module
        mock_ossv2 = Mock()
        mock_credentials = Mock()
        mock_config = Mock()
        mock_client = Mock()
        mock_paginator = Mock()

        mock_ossv2.credentials.EnvironmentVariableCredentialsProvider.return_value = (
            mock_credentials
        )
        mock_ossv2.config.load_default.return_value = mock_config
        mock_ossv2.Client.return_value = mock_client

        obj = Mock()
        obj.key = "data/file.parquet"
        obj.size = 1024
        obj.last_modified = datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC)

        page = Mock()
        page.contents = [obj]

        mock_iterator = iter([page])

        mock_client.list_objects_v2_paginator.return_value = mock_paginator
        mock_paginator.iter_page.return_value = mock_iterator

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2
        sys.modules["alibabacloud_oss_v2.credentials"] = mock_ossv2.credentials
        sys.modules["alibabacloud_oss_v2.config"] = mock_ossv2.config

        try:
            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            refs = asset.inspect()  # No client provided

            assert len(refs) == 1
            # Verify client was created
            mock_ossv2.Client.assert_called_once_with(mock_config)
        finally:
            for module in [
                "alibabacloud_oss_v2",
                "alibabacloud_oss_v2.credentials",
                "alibabacloud_oss_v2.config",
            ]:
                if module in sys.modules:
                    del sys.modules[module]

    def test_inspect_large_result_set(self):
        """Test inspect with large number of objects across multiple pages."""
        import sys

        mock_ossv2 = Mock()
        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            mock_client = Mock()
            mock_paginator = Mock()

            # Create 100 objects across 4 pages
            pages = []
            for page_idx in range(4):
                page = Mock()
                page.contents = []
                for obj_idx in range(25):
                    obj = Mock()
                    obj.key = f"data/file_{page_idx * 25 + obj_idx:04d}.parquet"
                    obj.size = 1024 * (page_idx * 25 + obj_idx + 1)
                    obj.last_modified = datetime(2024, 3, 15, 10, obj_idx, 0, tzinfo=UTC)
                    page.contents.append(obj)
                pages.append(page)

            mock_iterator = iter(pages)

            mock_client.list_objects_v2_paginator.return_value = mock_paginator
            mock_paginator.iter_page.return_value = mock_iterator

            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            refs = asset.inspect(client=mock_client)

            # Should collect all 100 objects
            assert len(refs) == 100
            # Verify ordering is preserved
            assert refs[0].uri == "oss://bucket/data/file_0000.parquet"
            assert refs[99].uri == "oss://bucket/data/file_0099.parquet"
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]

    def test_inspect_with_zero_size_objects(self):
        """Test inspect handles zero-size objects correctly."""
        import sys

        mock_ossv2 = Mock()
        sys.modules["alibabacloud_oss_v2"] = mock_ossv2

        try:
            mock_client = Mock()
            mock_paginator = Mock()

            obj = Mock()
            obj.key = "data/empty.parquet"
            obj.size = 0
            obj.last_modified = datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC)

            page = Mock()
            page.contents = [obj]

            mock_iterator = iter([page])

            mock_client.list_objects_v2_paginator.return_value = mock_paginator
            mock_paginator.iter_page.return_value = mock_iterator

            asset = OSSAsset(
                name="test",
                uri="oss://bucket/data/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
            )

            refs = asset.inspect(client=mock_client)

            assert len(refs) == 1
            assert refs[0].size == 0
        finally:
            if "alibabacloud_oss_v2" in sys.modules:
                del sys.modules["alibabacloud_oss_v2"]


# ============================================================================
# Integration Tests
# ============================================================================


class TestOSSAssetIntegration:
    """Integration tests for complete OSSAsset workflows."""

    def test_full_workflow_non_partitioned(self):
        """Test complete workflow: create asset, inspect, verify refs."""
        import sys

        # Setup mocks
        mock_ossv2 = Mock()
        mock_credentials = Mock()
        mock_config = Mock()
        mock_client = Mock()
        mock_paginator = Mock()

        mock_ossv2.credentials.EnvironmentVariableCredentialsProvider.return_value = (
            mock_credentials
        )
        mock_ossv2.config.load_default.return_value = mock_config
        mock_ossv2.Client.return_value = mock_client
        mock_ossv2.ListObjectsV2Request = Mock(return_value=Mock())

        obj1 = Mock()
        obj1.key = "sales/2024/data.parquet"
        obj1.size = 5120
        obj1.last_modified = datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC)

        obj2 = Mock()
        obj2.key = "sales/2024/metadata.json"
        obj2.size = 512
        obj2.last_modified = datetime(2024, 3, 15, 10, 5, 0, tzinfo=UTC)

        page = Mock()
        page.contents = [obj1, obj2]

        mock_iterator = iter([page])

        mock_client.list_objects_v2_paginator.return_value = mock_paginator
        mock_paginator.iter_page.return_value = mock_iterator

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2
        sys.modules["alibabacloud_oss_v2.credentials"] = mock_ossv2.credentials
        sys.modules["alibabacloud_oss_v2.config"] = mock_ossv2.config

        try:
            # Create asset
            asset = OSSAsset(
                name="sales_data",
                uri="oss://company-data/sales/",
                kind=AssetKind.PARQUET,
                region="oss-cn-hangzhou",
                description="Sales data for 2024",
            )

            # Inspect asset
            refs = asset.inspect()

            # Verify results
            assert len(refs) == 2
            assert asset.domain.name == "sales_data"
            assert asset.domain.bucket == "company-data"
            assert asset.domain.prefix == "sales/"

            # Verify first ref
            assert refs[0].bucket == "company-data"
            assert refs[0].size == 5120
            assert refs[0].partitions == {}

            # Verify second ref
            assert refs[1].size == 512
        finally:
            for module in [
                "alibabacloud_oss_v2",
                "alibabacloud_oss_v2.credentials",
                "alibabacloud_oss_v2.config",
            ]:
                if module in sys.modules:
                    del sys.modules[module]

    def test_full_workflow_partitioned(self):
        """Test complete workflow with partitioned data."""
        import sys

        # Setup mocks
        mock_ossv2 = Mock()
        mock_credentials = Mock()
        mock_config = Mock()
        mock_client = Mock()
        mock_paginator = Mock()

        mock_ossv2.credentials.EnvironmentVariableCredentialsProvider.return_value = (
            mock_credentials
        )
        mock_ossv2.config.load_default.return_value = mock_config
        mock_ossv2.Client.return_value = mock_client
        mock_ossv2.ListObjectsV2Request = Mock(return_value=Mock())

        obj1 = Mock()
        obj1.key = "events/year=2024/month=01/day=15/events.parquet"
        obj1.size = 10240
        obj1.last_modified = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        obj2 = Mock()
        obj2.key = "events/year=2024/month=01/day=16/events.parquet"
        obj2.size = 11264
        obj2.last_modified = datetime(2024, 1, 16, 10, 0, 0, tzinfo=UTC)

        page = Mock()
        page.contents = [obj1, obj2]

        mock_iterator = iter([page])

        mock_client.list_objects_v2_paginator.return_value = mock_paginator
        mock_paginator.iter_page.return_value = mock_iterator

        sys.modules["alibabacloud_oss_v2"] = mock_ossv2
        sys.modules["alibabacloud_oss_v2.credentials"] = mock_ossv2.credentials
        sys.modules["alibabacloud_oss_v2.config"] = mock_ossv2.config

        try:
            # Create partitioned asset
            asset = OSSAsset(
                name="events",
                uri="oss://analytics/events/",
                kind=AssetKind.PARQUET,
                region="oss-cn-shanghai",
                partitions=["year", "month", "day"],
            )

            # Inspect asset
            refs = asset.inspect()

            # Verify partitions
            assert len(refs) == 2
            assert refs[0].partitions == {"year": "2024", "month": "01", "day": "15"}
            assert refs[1].partitions == {"year": "2024", "month": "01", "day": "16"}

            # Verify URIs include full paths
            assert "year=2024/month=01/day=15" in refs[0].uri
            assert "year=2024/month=01/day=16" in refs[1].uri
        finally:
            for module in [
                "alibabacloud_oss_v2",
                "alibabacloud_oss_v2.credentials",
                "alibabacloud_oss_v2.config",
            ]:
                if module in sys.modules:
                    del sys.modules[module]
