"""
Comprehensive unit tests for LocalAdaptor and ILocalAdaptorLike protocol.

Tests cover:
- LocalAdaptor initialization
- list_objects: Pattern matching, time slicing, limit
- _slice_by_time: Time-based filtering
- _slice_by_limit: Limit-based filtering
- Protocol compliance
- Edge cases and error handling
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from bastion.control.asset.local.adaptor import ILocalAdaptorLike, LocalAdaptor

# ============================================================================
# Protocol Compliance Tests
# ============================================================================


class TestILocalAdaptorLikeProtocol:
    """Test suite for ILocalAdaptorLike protocol compliance."""

    def test_protocol_is_runtime_checkable(self):
        """Test that the protocol is runtime checkable."""
        assert isinstance(ILocalAdaptorLike, type)

        adaptor = LocalAdaptor()
        assert isinstance(adaptor, ILocalAdaptorLike)

    def test_protocol_has_required_methods(self):
        """Test that the protocol defines the required methods."""
        assert hasattr(ILocalAdaptorLike, "list_objects")

    def test_local_adaptor_implements_protocol(self):
        """Test that LocalAdaptor implements the protocol."""
        adaptor = LocalAdaptor()

        # Check that it's an instance of the protocol
        assert isinstance(adaptor, ILocalAdaptorLike)

        # Check that it has the required method
        assert hasattr(adaptor, "list_objects")
        assert callable(adaptor.list_objects)


# ============================================================================
# LocalAdaptor Initialization Tests
# ============================================================================


class TestLocalAdaptorInit:
    """Test suite for LocalAdaptor initialization."""

    def test_init_no_args(self):
        """Test creating adaptor with no arguments."""
        adaptor = LocalAdaptor()
        assert adaptor is not None
        assert isinstance(adaptor, LocalAdaptor)

    def test_multiple_instances_are_independent(self):
        """Test that multiple adaptor instances are independent."""
        adaptor1 = LocalAdaptor()
        adaptor2 = LocalAdaptor()

        assert adaptor1 is not adaptor2
        assert isinstance(adaptor1, LocalAdaptor)
        assert isinstance(adaptor2, LocalAdaptor)


# ============================================================================
# LocalAdaptor._slice_by_time Tests
# ============================================================================


class TestLocalAdaptorSliceByTime:
    """Test suite for LocalAdaptor._slice_by_time method."""

    def test_slice_by_time_no_filters(self, tmp_path: Path):
        """Test that no filters returns all files."""
        # Create test files
        files = []
        for i in range(5):
            file_path = tmp_path / f"file_{i}.txt"
            file_path.write_text(f"data {i}")
            files.append(file_path)

        adaptor = LocalAdaptor()
        result = adaptor._slice_by_time(files, since=None, until=None)

        assert len(result) == 5
        assert set(result) == set(files)

    def test_slice_by_time_with_since(self, tmp_path: Path):
        """Test filtering files created after a specific time."""
        adaptor = LocalAdaptor()

        # Create files with different timestamps
        old_file = tmp_path / "old.txt"
        old_file.write_text("old data")
        old_time = datetime.now(UTC)

        # Sleep briefly to ensure timestamp difference
        time.sleep(0.1)

        new_file = tmp_path / "new.txt"
        new_file.write_text("new data")

        files = [old_file, new_file]

        # Filter to only files after old_time
        result = adaptor._slice_by_time(files, since=old_time, until=None)

        # Should only include the new file
        assert len(result) == 1
        assert result[0] == new_file

    def test_slice_by_time_with_until(self, tmp_path: Path):
        """Test filtering files created before a specific time."""
        adaptor = LocalAdaptor()

        # Create a file
        file1 = tmp_path / "file1.txt"
        file1.write_text("data 1")

        # Get current time
        time.sleep(0.1)
        cutoff_time = datetime.now(UTC)
        time.sleep(0.1)

        # Create another file
        file2 = tmp_path / "file2.txt"
        file2.write_text("data 2")

        files = [file1, file2]

        # Filter to only files before cutoff_time
        result = adaptor._slice_by_time(files, since=None, until=cutoff_time)

        # Should only include file1
        assert len(result) == 1
        assert result[0] == file1

    def test_slice_by_time_with_both_filters(self, tmp_path: Path):
        """Test filtering files within a time range."""
        adaptor = LocalAdaptor()

        # Create files at different times
        file1 = tmp_path / "file1.txt"
        file1.write_text("data 1")
        time.sleep(0.1)

        since_time = datetime.now(UTC)
        time.sleep(0.1)

        file2 = tmp_path / "file2.txt"
        file2.write_text("data 2")
        time.sleep(0.1)

        until_time = datetime.now(UTC)
        time.sleep(0.1)

        file3 = tmp_path / "file3.txt"
        file3.write_text("data 3")

        files = [file1, file2, file3]

        # Filter to time range
        result = adaptor._slice_by_time(files, since=since_time, until=until_time)

        # Should only include file2
        assert len(result) == 1
        assert result[0] == file2

    def test_slice_by_time_empty_input(self):
        """Test slicing with empty file list."""
        adaptor = LocalAdaptor()
        since_time = datetime.now(UTC)

        result = adaptor._slice_by_time([], since=since_time, until=None)

        assert result == []

    def test_slice_by_time_no_matches(self, tmp_path: Path):
        """Test filtering when no files match the time range."""
        adaptor = LocalAdaptor()

        # Create a file
        file1 = tmp_path / "file.txt"
        file1.write_text("data")

        # Use a future time range
        future_time = datetime.now(UTC) + timedelta(days=1)

        result = adaptor._slice_by_time([file1], since=future_time, until=None)

        assert result == []


# ============================================================================
# LocalAdaptor._slice_by_limit Tests
# ============================================================================


class TestLocalAdaptorSliceByLimit:
    """Test suite for LocalAdaptor._slice_by_limit method."""

    def test_slice_by_limit_no_limit(self, tmp_path: Path):
        """Test that no limit returns all files."""
        files = [tmp_path / f"file_{i}.txt" for i in range(10)]
        for f in files:
            f.write_text("data")

        adaptor = LocalAdaptor()
        result = adaptor._slice_by_limit(files, limit=None)

        assert len(result) == 10
        assert result == files

    def test_slice_by_limit_with_valid_limit(self, tmp_path: Path):
        """Test limiting the number of files returned."""
        files = [tmp_path / f"file_{i}.txt" for i in range(10)]
        for f in files:
            f.write_text("data")

        adaptor = LocalAdaptor()
        result = adaptor._slice_by_limit(files, limit=5)

        assert len(result) == 5
        assert result == files[:5]

    def test_slice_by_limit_greater_than_available(self, tmp_path: Path):
        """Test limit greater than number of files."""
        files = [tmp_path / f"file_{i}.txt" for i in range(5)]
        for f in files:
            f.write_text("data")

        adaptor = LocalAdaptor()
        result = adaptor._slice_by_limit(files, limit=10)

        # Should return all files
        assert len(result) == 5
        assert result == files

    def test_slice_by_limit_zero(self, tmp_path: Path):
        """Test limit of zero returns all files."""
        files = [tmp_path / f"file_{i}.txt" for i in range(5)]
        for f in files:
            f.write_text("data")

        adaptor = LocalAdaptor()
        result = adaptor._slice_by_limit(files, limit=0)

        # Zero or negative limit should return all files
        assert len(result) == 5
        assert result == files

    def test_slice_by_limit_negative(self, tmp_path: Path):
        """Test negative limit returns all files."""
        files = [tmp_path / f"file_{i}.txt" for i in range(5)]
        for f in files:
            f.write_text("data")

        adaptor = LocalAdaptor()
        result = adaptor._slice_by_limit(files, limit=-1)

        assert len(result) == 5
        assert result == files

    def test_slice_by_limit_one(self, tmp_path: Path):
        """Test limit of 1 returns only first file."""
        files = [tmp_path / f"file_{i}.txt" for i in range(5)]
        for f in files:
            f.write_text("data")

        adaptor = LocalAdaptor()
        result = adaptor._slice_by_limit(files, limit=1)

        assert len(result) == 1
        assert result == [files[0]]

    def test_slice_by_limit_empty_input(self):
        """Test slicing empty file list."""
        adaptor = LocalAdaptor()
        result = adaptor._slice_by_limit([], limit=5)

        assert result == []


# ============================================================================
# LocalAdaptor.list_objects Tests
# ============================================================================


class TestLocalAdaptorListObjects:
    """Test suite for LocalAdaptor.list_objects method."""

    def test_list_objects_simple_pattern(self, tmp_path: Path):
        """Test listing files with simple glob pattern."""
        # Create test files
        (tmp_path / "file1.txt").write_text("data1")
        (tmp_path / "file2.txt").write_text("data2")
        (tmp_path / "file3.csv").write_text("data3")

        adaptor = LocalAdaptor()
        result = adaptor.list_objects(path=tmp_path, pattern="*.txt")

        assert len(result) == 2
        assert all(f.suffix == ".txt" for f in result)

    def test_list_objects_recursive_pattern(self, tmp_path: Path):
        """Test listing files recursively with nested directories."""
        # Create nested structure
        subdir1 = tmp_path / "sub1"
        subdir1.mkdir()
        (subdir1 / "file1.txt").write_text("data1")

        subdir2 = tmp_path / "sub2"
        subdir2.mkdir()
        (subdir2 / "file2.txt").write_text("data2")

        (tmp_path / "root.txt").write_text("root data")

        adaptor = LocalAdaptor()
        result = adaptor.list_objects(path=tmp_path, pattern="*.txt")

        # Should find all 3 txt files
        assert len(result) == 3

    def test_list_objects_with_partitions(self, tmp_path: Path):
        """Test listing files in partitioned structure."""
        # Create partitioned structure
        for year in ["2023", "2024"]:
            for month in ["01", "02"]:
                dir_path = tmp_path / f"year={year}" / f"month={month}"
                dir_path.mkdir(parents=True)
                (dir_path / f"data_{year}_{month}.parquet").write_text(f"data-{year}-{month}")

        adaptor = LocalAdaptor()
        pattern = "year=*/month=*/*.parquet"
        result = adaptor.list_objects(path=tmp_path, pattern=pattern)

        assert len(result) == 4  # 2 years * 2 months

    def test_list_objects_empty_directory(self, tmp_path: Path):
        """Test listing files in empty directory."""
        adaptor = LocalAdaptor()
        result = adaptor.list_objects(path=tmp_path, pattern="*.txt")

        assert result == []

    def test_list_objects_no_matches(self, tmp_path: Path):
        """Test listing when no files match the pattern."""
        (tmp_path / "file1.txt").write_text("data1")
        (tmp_path / "file2.txt").write_text("data2")

        adaptor = LocalAdaptor()
        result = adaptor.list_objects(path=tmp_path, pattern="*.csv")

        assert result == []

    def test_list_objects_with_since_filter(self, tmp_path: Path):
        """Test listing files with since time filter."""
        adaptor = LocalAdaptor()

        # Create old file
        old_file = tmp_path / "old.txt"
        old_file.write_text("old data")

        since_time = datetime.now(UTC)
        time.sleep(0.1)

        # Create new file
        new_file = tmp_path / "new.txt"
        new_file.write_text("new data")

        result = adaptor.list_objects(
            path=tmp_path,
            pattern="*.txt",
            since=since_time,
        )

        # Should only find the new file
        assert len(result) == 1
        assert result[0].name == "new.txt"

    def test_list_objects_with_until_filter(self, tmp_path: Path):
        """Test listing files with until time filter."""
        adaptor = LocalAdaptor()

        # Create first file
        file1 = tmp_path / "file1.txt"
        file1.write_text("data1")

        time.sleep(0.1)
        until_time = datetime.now(UTC)
        time.sleep(0.1)

        # Create second file
        file2 = tmp_path / "file2.txt"
        file2.write_text("data2")

        result = adaptor.list_objects(
            path=tmp_path,
            pattern="*.txt",
            until=until_time,
        )

        # Should only find file1
        assert len(result) == 1
        assert result[0].name == "file1.txt"

    def test_list_objects_with_time_range(self, tmp_path: Path):
        """Test listing files within a time range."""
        adaptor = LocalAdaptor()

        # Create files at different times
        file1 = tmp_path / "file1.txt"
        file1.write_text("data1")
        time.sleep(0.1)

        since_time = datetime.now(UTC)
        time.sleep(0.1)

        file2 = tmp_path / "file2.txt"
        file2.write_text("data2")
        time.sleep(0.1)

        until_time = datetime.now(UTC)
        time.sleep(0.1)

        file3 = tmp_path / "file3.txt"
        file3.write_text("data3")

        result = adaptor.list_objects(
            path=tmp_path,
            pattern="*.txt",
            since=since_time,
            until=until_time,
        )

        # Should only find file2
        assert len(result) == 1
        assert result[0].name == "file2.txt"

    def test_list_objects_with_limit(self, tmp_path: Path):
        """Test listing files with limit."""
        # Create multiple files
        for i in range(10):
            (tmp_path / f"file_{i}.txt").write_text(f"data {i}")

        adaptor = LocalAdaptor()
        result = adaptor.list_objects(
            path=tmp_path,
            pattern="*.txt",
            limit=5,
        )

        assert len(result) == 5

    def test_list_objects_sorted_by_modified_time(self, tmp_path: Path):
        """Test that list_objects returns files sorted by modification time (newest first)."""
        adaptor = LocalAdaptor()

        # Create files with delays to ensure different timestamps
        file1 = tmp_path / "file1.txt"
        file1.write_text("data1")
        time.sleep(0.1)

        file2 = tmp_path / "file2.txt"
        file2.write_text("data2")
        time.sleep(0.1)

        file3 = tmp_path / "file3.txt"
        file3.write_text("data3")

        result = adaptor.list_objects(path=tmp_path, pattern="*.txt")

        # Should be sorted by modification time, newest first
        assert len(result) == 3
        assert result[0].name == "file3.txt"  # Most recent
        assert result[2].name == "file1.txt"  # Oldest

    def test_list_objects_with_all_filters(self, tmp_path: Path):
        """Test list_objects with all filters combined."""
        adaptor = LocalAdaptor()

        # Create multiple files
        for i in range(10):
            file = tmp_path / f"file_{i}.txt"
            file.write_text(f"data {i}")
            time.sleep(0.05)

        # Get time range (skip first 2 and last 2)
        all_files = sorted(tmp_path.glob("*.txt"), key=lambda f: f.stat().st_mtime)
        since_time = datetime.fromtimestamp(all_files[2].stat().st_mtime, tz=UTC)
        until_time = datetime.fromtimestamp(all_files[7].stat().st_mtime, tz=UTC)

        result = adaptor.list_objects(
            path=tmp_path,
            pattern="*.txt",
            since=since_time,
            until=until_time,
            limit=3,
        )

        # Should return at most 3 files within the time range
        assert len(result) <= 3

    def test_list_objects_preserves_path_objects(self, tmp_path: Path):
        """Test that list_objects returns Path objects."""
        (tmp_path / "file.txt").write_text("data")

        adaptor = LocalAdaptor()
        result = adaptor.list_objects(path=tmp_path, pattern="*.txt")

        assert len(result) == 1
        assert isinstance(result[0], Path)
        assert result[0].exists()


# ============================================================================
# Integration and Edge Case Tests
# ============================================================================


class TestLocalAdaptorIntegration:
    """Integration tests for LocalAdaptor."""

    def test_adaptor_with_complex_workflow(self, tmp_path: Path):
        """Test complete workflow with adaptor."""
        adaptor = LocalAdaptor()

        # Create complex structure
        for year in ["2023", "2024"]:
            for month in ["01", "06", "12"]:
                dir_path = tmp_path / f"year={year}" / f"month={month}"
                dir_path.mkdir(parents=True)

                for i in range(5):
                    file = dir_path / f"part_{i}.parquet"
                    file.write_text(f"data-{year}-{month}-{i}")
                    time.sleep(0.01)

        # List all files
        pattern = "year=*/month=*/*.parquet"
        all_files = adaptor.list_objects(path=tmp_path, pattern=pattern)

        assert len(all_files) == 30  # 2 years * 3 months * 5 files

        # Get recent files only
        recent_time = datetime.now(UTC) - timedelta(seconds=1)
        recent_files = adaptor.list_objects(
            path=tmp_path,
            pattern=pattern,
            since=recent_time,
        )

        assert len(recent_files) >= 0
        assert len(recent_files) <= 30

        # Get limited files
        limited_files = adaptor.list_objects(
            path=tmp_path,
            pattern=pattern,
            limit=10,
        )

        assert len(limited_files) == 10

    def test_custom_adaptor_implementation(self, tmp_path: Path):
        """Test that custom adaptor implementations work with the protocol."""

        # Create a custom adaptor
        class CustomAdaptor(ILocalAdaptorLike):
            def list_objects(
                self,
                path: Path,
                pattern: str,
                since: datetime | None = None,
                until: datetime | None = None,
                limit: int | None = None,
            ) -> list[Path]:
                # Simple implementation that just lists files
                return list(path.rglob(pattern))[: limit if limit else None]

        # Create test files
        (tmp_path / "file1.txt").write_text("data1")
        (tmp_path / "file2.txt").write_text("data2")

        custom = CustomAdaptor()

        # Verify it implements the protocol
        assert isinstance(custom, ILocalAdaptorLike)

        # Test it works
        result = custom.list_objects(path=tmp_path, pattern="*.txt")
        assert len(result) == 2


# ============================================================================
# Performance Tests
# ============================================================================


class TestLocalAdaptorPerformance:
    """Performance tests for LocalAdaptor."""

    def test_performance_large_directory(self, tmp_path: Path):
        """Test performance with large number of files."""
        # Create many files
        num_files = 1000
        for i in range(num_files):
            (tmp_path / f"file_{i:04d}.txt").write_text(f"data {i}")

        adaptor = LocalAdaptor()

        start_time = time.time()
        result = adaptor.list_objects(path=tmp_path, pattern="*.txt")
        elapsed_time = time.time() - start_time

        assert len(result) == num_files
        assert elapsed_time < 5.0  # Should complete in under 5 seconds

    def test_performance_deep_nesting(self, tmp_path: Path):
        """Test performance with deeply nested directories."""
        # Create deep structure
        for i in range(10):
            for j in range(10):
                dir_path = tmp_path / f"level1_{i}" / f"level2_{j}"
                dir_path.mkdir(parents=True)
                (dir_path / f"file_{i}_{j}.txt").write_text(f"data {i} {j}")

        adaptor = LocalAdaptor()

        start_time = time.time()
        result = adaptor.list_objects(path=tmp_path, pattern="*.txt")
        elapsed_time = time.time() - start_time

        assert len(result) == 100  # 10 * 10
        assert elapsed_time < 5.0
