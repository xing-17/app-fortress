"""
Unit tests for S3Adaptor and IS3AdaptorLike protocol.

Tests cover:
- S3Adaptor initialization
- Protocol compliance
- list_objects: Basic functionality, time slicing, limit
- _slice_by_time: Time-based filtering
- _slice_by_limit: Limit-based filtering
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol
from unittest.mock import MagicMock, Mock, patch

import pytest

from bastion.control.asset.s3.adaptor import IS3AdaptorLike, S3Adaptor


# ============================================================================
# Protocol Compliance Tests
# ============================================================================


class TestIS3AdaptorLikeProtocol:
    """Test suite for IS3AdaptorLike protocol compliance."""

    def test_protocol_is_runtime_checkable(self):
        """Test that the protocol is runtime checkable."""
        assert isinstance(IS3AdaptorLike, type)
        
        adaptor = S3Adaptor()
        assert isinstance(adaptor, IS3AdaptorLike)

    def test_protocol_has_required_methods(self):
        """Test that the protocol defines the required methods."""
        assert hasattr(IS3AdaptorLike, "list_objects")

    def test_s3_adaptor_implements_protocol(self):
        """Test that S3Adaptor implements the protocol."""
        adaptor = S3Adaptor()
        
        # Check that it's an instance of the protocol
        assert isinstance(adaptor, IS3AdaptorLike)
        
        # Check that it has the required method
        assert hasattr(adaptor, "list_objects")
        assert callable(adaptor.list_objects)


# ============================================================================
# S3Adaptor Initialization Tests
# ============================================================================


class TestS3AdaptorInit:
    """Test suite for S3Adaptor initialization."""

    def test_init_no_args(self):
        """Test creating adaptor with no arguments."""
        adaptor = S3Adaptor()
        assert adaptor is not None
        assert isinstance(adaptor, S3Adaptor)

    def test_init_with_credentials(self):
        """Test creating adaptor with AWS credentials."""
        adaptor = S3Adaptor(
            access_key_id="test_key",
            access_key_secret="test_secret",
            region="us-west-2",
        )
        assert adaptor is not None
        assert adaptor._creds["aws_access_key_id"] == "test_key"
        assert adaptor._creds["aws_secret_access_key"] == "test_secret"
        assert adaptor._creds["region_name"] == "us-west-2"

    def test_init_with_profile(self):
        """Test creating adaptor with AWS profile."""
        adaptor = S3Adaptor(profile="my-profile")
        assert adaptor._creds["profile_name"] == "my-profile"

    def test_multiple_instances_are_independent(self):
        """Test that multiple adaptor instances are independent."""
        adaptor1 = S3Adaptor(region="us-east-1")
        adaptor2 = S3Adaptor(region="us-west-2")
        
        assert adaptor1 is not adaptor2
        assert adaptor1._creds["region_name"] == "us-east-1"
        assert adaptor2._creds["region_name"] == "us-west-2"


# ============================================================================
# S3Adaptor._slice_by_time Tests
# ============================================================================


class TestS3AdaptorSliceByTime:
    """Test suite for S3Adaptor._slice_by_time method."""

    def test_slice_by_time_no_filters(self):
        """Test that no filters returns all files."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": "file1.txt", "Size": 100, "LastModified": datetime(2024, 1, 1, tzinfo=UTC)},
            {"Key": "file2.txt", "Size": 200, "LastModified": datetime(2024, 1, 2, tzinfo=UTC)},
            {"Key": "file3.txt", "Size": 300, "LastModified": datetime(2024, 1, 3, tzinfo=UTC)},
        ]
        
        result = adaptor._slice_by_time(files, since=None, until=None)
        
        assert len(result) == 3
        assert result == files

    def test_slice_by_time_with_since(self):
        """Test filtering files modified after a specific time."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": "old.txt", "Size": 100, "LastModified": datetime(2024, 1, 1, tzinfo=UTC)},
            {"Key": "new.txt", "Size": 200, "LastModified": datetime(2024, 1, 10, tzinfo=UTC)},
        ]
        
        since_time = datetime(2024, 1, 5, tzinfo=UTC)
        result = adaptor._slice_by_time(files, since=since_time, until=None)
        
        # Should only include the new file
        assert len(result) == 1
        assert result[0]["Key"] == "new.txt"

    def test_slice_by_time_with_until(self):
        """Test filtering files modified before a specific time."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": "file1.txt", "Size": 100, "LastModified": datetime(2024, 1, 1, tzinfo=UTC)},
            {"Key": "file2.txt", "Size": 200, "LastModified": datetime(2024, 1, 10, tzinfo=UTC)},
        ]
        
        until_time = datetime(2024, 1, 5, tzinfo=UTC)
        result = adaptor._slice_by_time(files, since=None, until=until_time)
        
        # Should only include file1
        assert len(result) == 1
        assert result[0]["Key"] == "file1.txt"

    def test_slice_by_time_with_both_filters(self):
        """Test filtering files within a time range."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": "file1.txt", "Size": 100, "LastModified": datetime(2024, 1, 1, tzinfo=UTC)},
            {"Key": "file2.txt", "Size": 200, "LastModified": datetime(2024, 1, 5, tzinfo=UTC)},
            {"Key": "file3.txt", "Size": 300, "LastModified": datetime(2024, 1, 10, tzinfo=UTC)},
        ]
        
        since_time = datetime(2024, 1, 2, tzinfo=UTC)
        until_time = datetime(2024, 1, 8, tzinfo=UTC)
        result = adaptor._slice_by_time(files, since=since_time, until=until_time)
        
        # Should only include file2
        assert len(result) == 1
        assert result[0]["Key"] == "file2.txt"

    def test_slice_by_time_empty_input(self):
        """Test slicing with empty file list."""
        adaptor = S3Adaptor()
        since_time = datetime.now(UTC)
        
        result = adaptor._slice_by_time([], since=since_time, until=None)
        
        assert result == []

    def test_slice_by_time_no_matches(self):
        """Test filtering when no files match the time range."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": "file.txt", "Size": 100, "LastModified": datetime(2024, 1, 1, tzinfo=UTC)},
        ]
        
        # Time range that excludes all files
        since_time = datetime(2024, 1, 10, tzinfo=UTC)
        result = adaptor._slice_by_time(files, since=since_time, until=None)
        
        assert result == []

    def test_slice_by_time_missing_modified_at(self):
        """Test handling files without LastModified field."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": "file1.txt", "Size": 100},  # No LastModified
            {"Key": "file2.txt", "Size": 200, "LastModified": datetime(2024, 1, 5, tzinfo=UTC)},
        ]
        
        since_time = datetime(2024, 1, 1, tzinfo=UTC)
        result = adaptor._slice_by_time(files, since=since_time, until=None)
        
        # Should only include file2 (file1 is skipped due to missing LastModified)
        assert len(result) == 1
        assert result[0]["Key"] == "file2.txt"


# ============================================================================
# S3Adaptor._slice_by_limit Tests
# ============================================================================


class TestS3AdaptorSliceByLimit:
    """Test suite for S3Adaptor._slice_by_limit method."""

    def test_slice_by_limit_none(self):
        """Test that None limit returns all files."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": f"file{i}.txt", "Size": 100} for i in range(5)
        ]
        
        result = adaptor._slice_by_limit(files, limit=None)
        
        assert len(result) == 5
        assert result == files

    def test_slice_by_limit_valid(self):
        """Test limiting to a specific number of files."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": f"file{i}.txt", "Size": 100} for i in range(10)
        ]
        
        result = adaptor._slice_by_limit(files, limit=3)
        
        assert len(result) == 3
        assert result == files[:3]

    def test_slice_by_limit_exceeds_length(self):
        """Test limit greater than file count."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": f"file{i}.txt", "Size": 100} for i in range(3)
        ]
        
        result = adaptor._slice_by_limit(files, limit=10)
        
        assert len(result) == 3
        assert result == files

    def test_slice_by_limit_zero(self):
        """Test zero limit returns all files."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": f"file{i}.txt", "Size": 100} for i in range(5)
        ]
        
        result = adaptor._slice_by_limit(files, limit=0)
        
        assert len(result) == 5

    def test_slice_by_limit_negative(self):
        """Test negative limit returns all files."""
        adaptor = S3Adaptor()
        
        files = [
            {"Key": f"file{i}.txt", "Size": 100} for i in range(5)
        ]
        
        result = adaptor._slice_by_limit(files, limit=-1)
        
        assert len(result) == 5

    def test_slice_by_limit_empty_list(self):
        """Test limiting empty file list."""
        adaptor = S3Adaptor()
        
        result = adaptor._slice_by_limit([], limit=5)
        
        assert result == []


# ============================================================================
# S3Adaptor.list_objects Tests (with mocking)
# ============================================================================


class TestS3AdaptorListObjects:
    """Test suite for S3Adaptor.list_objects method with mocked boto3."""

    def test_list_objects_basic(self):
        """Test basic list_objects functionality."""
        adaptor = S3Adaptor()
        
        # Mock boto3 client
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "path/file1.txt",
                        "Size": 100,
                        "LastModified": datetime(2024, 1, 1, tzinfo=UTC),
                    },
                    {
                        "Key": "path/file2.txt",
                        "Size": 200,
                        "LastModified": datetime(2024, 1, 2, tzinfo=UTC),
                    },
                ]
            }
        ]
        
        mock_paginator.paginate.return_value = mock_iterator
        mock_client.get_paginator.return_value = mock_paginator
        
        with patch.object(adaptor, "_get_client", return_value=mock_client):
            result = adaptor.list_objects(bucket="test-bucket", prefix="path/")
        
        assert len(result) == 2
        assert result[0]["Key"] == "path/file2.txt"  # Sorted by LastModified, reverse=True
        assert result[1]["Key"] == "path/file1.txt"

    def test_list_objects_with_time_filters(self):
        """Test list_objects with time filtering."""
        adaptor = S3Adaptor()
        
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": "file1.txt",
                        "Size": 100,
                        "LastModified": datetime(2024, 1, 1, tzinfo=UTC),
                    },
                    {
                        "Key": "file2.txt",
                        "Size": 200,
                        "LastModified": datetime(2024, 1, 5, tzinfo=UTC),
                    },
                    {
                        "Key": "file3.txt",
                        "Size": 300,
                        "LastModified": datetime(2024, 1, 10, tzinfo=UTC),
                    },
                ]
            }
        ]
        
        mock_paginator.paginate.return_value = mock_iterator
        mock_client.get_paginator.return_value = mock_paginator
        
        with patch.object(adaptor, "_get_client", return_value=mock_client):
            result = adaptor.list_objects(
                bucket="test-bucket",
                prefix="",
                since=datetime(2024, 1, 2, tzinfo=UTC),
                until=datetime(2024, 1, 8, tzinfo=UTC),
            )
        
        # Should only return file2
        assert len(result) == 1
        assert result[0]["Key"] == "file2.txt"

    def test_list_objects_with_limit(self):
        """Test list_objects with limit."""
        adaptor = S3Adaptor()
        
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_iterator = [
            {
                "Contents": [
                    {
                        "Key": f"file{i}.txt",
                        "Size": 100,
                        "LastModified": datetime(2024, 1, i, tzinfo=UTC),
                    }
                    for i in range(1, 6)
                ]
            }
        ]
        
        mock_paginator.paginate.return_value = mock_iterator
        mock_client.get_paginator.return_value = mock_paginator
        
        with patch.object(adaptor, "_get_client", return_value=mock_client):
            result = adaptor.list_objects(
                bucket="test-bucket",
                prefix="",
                limit=2,
            )
        
        # Should only return first 2 files (after sorting)
        assert len(result) == 2

    def test_list_objects_empty_bucket(self):
        """Test list_objects with empty bucket."""
        adaptor = S3Adaptor()
        
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_iterator = [{"Contents": []}]
        
        mock_paginator.paginate.return_value = mock_iterator
        mock_client.get_paginator.return_value = mock_paginator
        
        with patch.object(adaptor, "_get_client", return_value=mock_client):
            result = adaptor.list_objects(bucket="test-bucket", prefix="path/")
        
        assert result == []

    def test_list_objects_no_contents_key(self):
        """Test list_objects when page has no Contents key."""
        adaptor = S3Adaptor()
        
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_iterator = [{}]  # No Contents key
        
        mock_paginator.paginate.return_value = mock_iterator
        mock_client.get_paginator.return_value = mock_paginator
        
        with patch.object(adaptor, "_get_client", return_value=mock_client):
            result = adaptor.list_objects(bucket="test-bucket", prefix="path/")
        
        assert result == []
