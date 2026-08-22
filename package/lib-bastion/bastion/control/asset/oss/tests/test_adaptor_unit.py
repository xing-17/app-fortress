"""
Unit tests for OSSAdaptor and IOSSAdaptorLike protocol.

Tests cover:
- IOSSAdaptorLike protocol compliance
- OSSAdaptor initialization
- _slice_by_time: Time-based filtering
- _slice_by_limit: Limit-based filtering
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from bastion.control.asset.oss.adaptor import IOSSAdaptorLike, OSSAdaptor

# ============================================================================
# Protocol Compliance Tests
# ============================================================================


class TestIOSSAdaptorLikeProtocol:
    """Test suite for IOSSAdaptorLike protocol compliance."""

    def test_protocol_is_runtime_checkable(self):
        """Test that the protocol is runtime checkable."""
        assert isinstance(IOSSAdaptorLike, type)

    def test_protocol_has_required_methods(self):
        """Test that the protocol defines the required methods."""
        assert hasattr(IOSSAdaptorLike, "list_objects")

    def test_oss_adaptor_implements_protocol(self):
        """Test that OSSAdaptor implements the protocol."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")

        assert isinstance(adaptor, IOSSAdaptorLike)
        assert hasattr(adaptor, "list_objects")
        assert callable(adaptor.list_objects)


# ============================================================================
# OSSAdaptor Initialization Tests
# ============================================================================


class TestOSSAdaptorInit:
    """Test suite for OSSAdaptor initialization."""

    def test_init_with_region_only(self):
        """Test creating adaptor with only region."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")

        assert adaptor.region == "oss-cn-hangzhou"
        assert adaptor.endpoint is None

    def test_init_with_region_and_endpoint(self):
        """Test creating adaptor with region and endpoint."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou", endpoint="oss-cn-hangzhou.aliyuncs.com")

        assert adaptor.region == "oss-cn-hangzhou"
        assert adaptor.endpoint == "oss-cn-hangzhou.aliyuncs.com"

    def test_init_with_credentials(self):
        """Test creating adaptor with credentials."""
        adaptor = OSSAdaptor(
            region="oss-cn-hangzhou", access_key_id="test_key", access_key_secret="test_secret"
        )

        assert adaptor._creds["access_key_id"] == "test_key"
        assert adaptor._creds["access_key_secret"] == "test_secret"


# ============================================================================
# OSSAdaptor._slice_by_time Tests
# ============================================================================


class TestOSSAdaptorSliceByTime:
    """Test suite for OSSAdaptor._slice_by_time method."""

    def _create_mock_file(self, last_modified: datetime) -> Mock:
        """Helper to create a mock OSS file object."""
        mock_file = Mock()
        mock_dt = Mock()
        mock_dt.as_timezone.return_value = last_modified
        mock_file.last_modified = mock_dt
        return mock_file

    def test_slice_by_time_no_filters(self):
        """Test that no filters returns all files."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")
        now = datetime.now(UTC)

        files = [
            self._create_mock_file(now - timedelta(hours=3)),
            self._create_mock_file(now - timedelta(hours=2)),
            self._create_mock_file(now - timedelta(hours=1)),
        ]

        result = adaptor._slice_by_time(files, since=None, until=None)

        assert len(result) == 3
        assert result == files

    def test_slice_by_time_with_since(self):
        """Test filtering files modified after a specific time."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")
        now = datetime.now(UTC)
        since_time = now - timedelta(hours=2)

        files = [
            self._create_mock_file(now - timedelta(hours=3)),
            self._create_mock_file(now - timedelta(hours=1)),
            self._create_mock_file(now),
        ]

        result = adaptor._slice_by_time(files, since=since_time, until=None)

        assert len(result) == 2

    def test_slice_by_time_with_until(self):
        """Test filtering files modified before a specific time."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")
        now = datetime.now(UTC)
        until_time = now - timedelta(hours=1)

        files = [
            self._create_mock_file(now - timedelta(hours=3)),
            self._create_mock_file(now - timedelta(hours=2)),
            self._create_mock_file(now),
        ]

        result = adaptor._slice_by_time(files, since=None, until=until_time)

        assert len(result) == 2

    def test_slice_by_time_with_both_filters(self):
        """Test filtering files within a time range."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")
        now = datetime.now(UTC)
        since_time = now - timedelta(hours=3)
        until_time = now - timedelta(hours=1)

        files = [
            self._create_mock_file(now - timedelta(hours=4)),
            self._create_mock_file(now - timedelta(hours=2)),
            self._create_mock_file(now),
        ]

        result = adaptor._slice_by_time(files, since=since_time, until=until_time)

        assert len(result) == 1

    def test_slice_by_time_empty_input(self):
        """Test slicing with empty file list."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")
        now = datetime.now(UTC)

        result = adaptor._slice_by_time([], since=now, until=None)

        assert result == []


# ============================================================================
# OSSAdaptor._slice_by_limit Tests
# ============================================================================


class TestOSSAdaptorSliceByLimit:
    """Test suite for OSSAdaptor._slice_by_limit method."""

    def test_slice_by_limit_no_limit(self):
        """Test that None limit returns all files."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")
        files = [Mock() for _ in range(5)]

        result = adaptor._slice_by_limit(files, limit=None)

        assert len(result) == 5
        assert result == files

    def test_slice_by_limit_with_limit(self):
        """Test limiting the number of files."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")
        files = [Mock() for _ in range(10)]

        result = adaptor._slice_by_limit(files, limit=3)

        assert len(result) == 3
        assert result == files[:3]

    def test_slice_by_limit_zero(self):
        """Test that zero limit returns all files."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")
        files = [Mock() for _ in range(5)]

        result = adaptor._slice_by_limit(files, limit=0)

        assert len(result) == 5
        assert result == files

    def test_slice_by_limit_exceeds_count(self):
        """Test that limit exceeding file count returns all files."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")
        files = [Mock() for _ in range(3)]

        result = adaptor._slice_by_limit(files, limit=10)

        assert len(result) == 3
        assert result == files

    def test_slice_by_limit_empty_input(self):
        """Test limiting with empty file list."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")

        result = adaptor._slice_by_limit([], limit=5)

        assert result == []


# ============================================================================
# OSSAdaptor Client Creation Tests
# ============================================================================


class TestOSSAdaptorClientCreation:
    """Test suite for OSSAdaptor client creation methods."""

    def test_get_client_missing_dependency(self):
        """Test that missing dependency raises ImportError."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")

        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'alibabacloud_oss_v2'")
        ):
            with pytest.raises(ImportError, match="alibabacloud_oss_v2 is required"):
                adaptor._get_client()

    def test_get_request_missing_dependency(self):
        """Test that missing dependency in request creation raises ImportError."""
        adaptor = OSSAdaptor(region="oss-cn-hangzhou")

        with patch("builtins.__import__", side_effect=ImportError("No module")):
            with pytest.raises(ImportError, match="alibabacloud_oss_v2 is required"):
                adaptor._get_oss_request(bucket="test-bucket", prefix="test/")
