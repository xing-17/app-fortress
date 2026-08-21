"""
Comprehensive unit tests for LocalAsset, LocalAssetModel, and LocalAssetRef classes.

Tests cover:
- LocalAssetRef: URI parsing, name/stem extraction
- LocalAssetModel: Domain model validation
- LocalAsset: Path resolution, glob patterns, partition extraction, file inspection
- Performance: Smoke test with large directory structures
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from bastion.control.asset.local.local import (
    LocalAsset,
    LocalAssetModel,
    LocalAssetRef,
)
from bastion.domain.assetkind import AssetKind
from bastion.domain.platform import Platform


# ============================================================================
# LocalAssetRef Tests
# ============================================================================


class TestLocalAssetRef:
    """Test suite for LocalAssetRef class."""

    def test_name_computed_field(self):
        """Test that name returns the filename from URI."""
        ref = LocalAssetRef(
            uri="/home/user/data/sales.parquet",
            partitions={},
            size=1024,
        )
        assert ref.name == "sales.parquet"

    def test_stem_computed_field(self):
        """Test that stem returns filename without extension."""
        ref = LocalAssetRef(
            uri="/home/user/data/sales.parquet",
            partitions={},
            size=1024,
        )
        assert ref.stem == "sales"

    def test_name_with_multiple_extensions(self):
        """Test name with double extensions like .tar.gz."""
        ref = LocalAssetRef(
            uri="/data/backup.tar.gz",
            partitions={},
            size=2048,
        )
        assert ref.name == "backup.tar.gz"
        assert ref.stem == "backup.tar"

    def test_name_with_complex_path(self):
        """Test name extraction from complex nested paths."""
        ref = LocalAssetRef(
            uri="/data/year=2024/month=01/day=15/transactions.csv",
            partitions={"year": "2024", "month": "01", "day": "15"},
            size=4096,
        )
        assert ref.name == "transactions.csv"
        assert ref.stem == "transactions"

    def test_ref_with_metadata(self):
        """Test LocalAssetRef with all metadata fields."""
        modified = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

        ref = LocalAssetRef(
            uri="/data/file.parquet",
            partitions={"year": "2024"},
            size=8192,
            modified_at=modified,
        )

        assert ref.size == 8192
        assert ref.modified_at == modified
        assert ref.partitions == {"year": "2024"}

    def test_ref_without_partitions(self):
        """Test LocalAssetRef with empty partitions."""
        ref = LocalAssetRef(
            uri="/data/simple.csv",
            partitions={},
            size=512,
        )
        assert ref.partitions == {}
        assert ref.name == "simple.csv"


# ============================================================================
# LocalAssetModel Tests
# ============================================================================


class TestLocalAssetModel:
    """Test suite for LocalAssetModel domain model."""

    def test_model_creation_with_required_fields(self):
        """Test creating a model with all required fields."""
        model = LocalAssetModel(
            name="test_asset",
            path="/home/user/data",
            kind=AssetKind.PARQUET,
        )

        assert model.name == "test_asset"
        assert model.path == "/home/user/data"
        assert model.kind == AssetKind.PARQUET
        assert model.platform == Platform.LOCAL

    def test_model_platform_defaults_to_local(self):
        """Test that platform defaults to LOCAL."""
        model = LocalAssetModel(
            name="sales",
            path="/data/sales",
            kind=AssetKind.CSV,
        )
        assert model.platform == Platform.LOCAL

    def test_model_with_partitions(self):
        """Test model with partition columns."""
        model = LocalAssetModel(
            name="partitioned_data",
            path="/data/warehouse",
            kind=AssetKind.PARQUET,
            partitions=["year", "month", "day"],
        )

        assert model.partitions == ["year", "month", "day"]

    def test_model_with_metadata(self):
        """Test model with optional metadata fields."""
        model = LocalAssetModel(
            name="enriched_asset",
            path="/data/enriched",
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
        ref = LocalAssetRef(
            uri="/data/file.parquet",
            partitions={},
            size=1024,
        )

        model = LocalAssetModel(
            name="asset_with_refs",
            path="/data",
            kind=AssetKind.PARQUET,
            refs=[ref],
        )

        assert len(model.refs) == 1
        assert model.refs[0].uri == "/data/file.parquet"


# ============================================================================
# LocalAsset Tests
# ============================================================================


class TestLocalAssetResolvePath:
    """Test suite for LocalAsset._resolve_path method."""

    def test_resolve_absolute_path(self, tmp_path: Path):
        """Test resolution of absolute paths."""
        asset = LocalAsset(
            name="test",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        resolved = asset._resolve_path()
        assert resolved == tmp_path
        assert resolved.is_absolute()

    def test_resolve_path_with_tilde(self, monkeypatch: pytest.MonkeyPatch):
        """Test path expansion with ~ (home directory)."""
        asset = LocalAsset(
            name="test",
            path="~/data/test",
            kind=AssetKind.CSV,
            platform=Platform.LOCAL,
        )

        resolved = asset._resolve_path()
        assert "~" not in str(resolved)
        assert resolved.is_absolute()

    def test_resolve_relative_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test resolution of relative paths."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        asset = LocalAsset(
            name="test",
            path="./data",
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        resolved = asset._resolve_path()
        assert resolved.is_absolute()
        assert tmp_path in resolved.parents or resolved == tmp_path / "data"

    def test_resolve_path_with_double_dots(self, tmp_path: Path):
        """Test path resolution with parent directory (..)."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        asset = LocalAsset(
            name="test",
            path=str(subdir / "../data"),
            kind=AssetKind.CSV,
            platform=Platform.LOCAL,
        )

        resolved = asset._resolve_path()
        assert ".." not in str(resolved)
        assert resolved == tmp_path / "data"


class TestLocalAssetResolveGlobPattern:
    """Test suite for LocalAsset._resolve_glob_pattern method."""

    def test_glob_pattern_without_partitions(self):
        """Test glob pattern for non-partitioned data."""
        asset = LocalAsset(
            name="simple",
            path="/data",
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        pattern = asset._resolve_glob_pattern()
        assert pattern == "*parquet"

    def test_glob_pattern_with_single_partition(self):
        """Test glob pattern with one partition column."""
        asset = LocalAsset(
            name="partitioned",
            path="/data",
            kind=AssetKind.CSV,
            platform=Platform.LOCAL,
            partitions=["year"],
        )

        pattern = asset._resolve_glob_pattern()
        assert pattern == "year=*/*csv"

    def test_glob_pattern_with_multiple_partitions(self):
        """Test glob pattern with multiple partition columns."""
        asset = LocalAsset(
            name="multi_partitioned",
            path="/data",
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["year", "month", "day"],
        )

        pattern = asset._resolve_glob_pattern()
        expected = str(Path("year=*") / "month=*" / "day=*" / "*parquet")
        assert pattern == expected

    def test_glob_pattern_with_csv_format(self):
        """Test glob pattern for CSV files."""
        asset = LocalAsset(
            name="csv_data",
            path="/data",
            kind=AssetKind.CSV,
            platform=Platform.LOCAL,
            partitions=["category"],
        )

        pattern = asset._resolve_glob_pattern()
        assert pattern.endswith("csv")
        assert "category=*" in pattern


class TestLocalAssetResolvePartition:
    """Test suite for LocalAsset._resolve_partition method."""

    def test_resolve_single_partition(self, tmp_path: Path):
        """Test extracting a single partition value."""
        asset = LocalAsset(
            name="test",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["year"],
        )

        file_path = tmp_path / "year=2024" / "data.parquet"
        partitions = asset._resolve_partition(file_path)

        assert partitions == {"year": "2024"}

    def test_resolve_multiple_partitions(self, tmp_path: Path):
        """Test extracting multiple partition values."""
        asset = LocalAsset(
            name="test",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["year", "month", "day"],
        )

        file_path = tmp_path / "year=2024" / "month=03" / "day=15" / "data.parquet"
        partitions = asset._resolve_partition(file_path)

        assert partitions == {"year": "2024", "month": "03", "day": "15"}

    def test_resolve_partition_with_no_partitions(self, tmp_path: Path):
        """Test that non-partitioned assets return empty dict."""
        asset = LocalAsset(
            name="test",
            path=str(tmp_path),
            kind=AssetKind.CSV,
            platform=Platform.LOCAL,
        )

        file_path = tmp_path / "data.csv"
        partitions = asset._resolve_partition(file_path)

        assert partitions == {}

    def test_resolve_partition_ignores_non_partition_dirs(self, tmp_path: Path):
        """Test that non-partition directories are ignored."""
        asset = LocalAsset(
            name="test",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["year", "month"],
        )

        file_path = tmp_path / "other" / "year=2024" / "month=06" / "file.parquet"
        partitions = asset._resolve_partition(file_path)

        # Should only extract the defined partition columns
        assert partitions == {"year": "2024", "month": "06"}
        assert "other" not in partitions

    def test_resolve_partition_with_special_values(self, tmp_path: Path):
        """Test partition extraction with special characters in values."""
        asset = LocalAsset(
            name="test",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["region", "category"],
        )

        file_path = tmp_path / "region=us-west-1" / "category=tech_hardware" / "data.parquet"
        partitions = asset._resolve_partition(file_path)

        assert partitions == {"region": "us-west-1", "category": "tech_hardware"}


class TestLocalAssetInspect:
    """Test suite for LocalAsset.inspect method."""

    def test_inspect_non_existent_path(self, tmp_path: Path):
        """Test inspect on non-existent directory."""
        non_existent = tmp_path / "does_not_exist"

        asset = LocalAsset(
            name="test",
            path=str(non_existent),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        refs = asset.inspect()
        assert refs == []
        assert asset.domain.refs == []

    def test_inspect_path_is_file(self, tmp_path: Path):
        """Test inspect when path points to a file instead of directory."""
        file_path = tmp_path / "single_file.parquet"
        file_path.write_text("test data")

        asset = LocalAsset(
            name="test",
            path=str(file_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        refs = asset.inspect()
        assert refs == []

    def test_inspect_simple_files(self, tmp_path: Path):
        """Test inspect with simple non-partitioned files."""
        # Create test files
        (tmp_path / "file1.parquet").write_text("data1")
        (tmp_path / "file2.parquet").write_text("data2")
        (tmp_path / "file3.csv").write_text("data3")  # Different format

        asset = LocalAsset(
            name="test",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        refs = asset.inspect()

        assert len(refs) == 2  # Only .parquet files
        assert all(ref.name.endswith(".parquet") for ref in refs)
        assert set(ref.name for ref in refs) == {"file1.parquet", "file2.parquet"}

        # Verify metadata
        for ref in refs:
            assert ref.size > 0
            assert ref.modified_at is not None
            assert ref.partitions == {}

    def test_inspect_partitioned_files(self, tmp_path: Path):
        """Test inspect with partitioned directory structure."""
        # Create partitioned structure
        for year in ["2023", "2024"]:
            for month in ["01", "02"]:
                dir_path = tmp_path / f"year={year}" / f"month={month}"
                dir_path.mkdir(parents=True)
                (dir_path / f"data_{year}_{month}.parquet").write_text(f"data-{year}-{month}")

        asset = LocalAsset(
            name="partitioned",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["year", "month"],
        )

        refs = asset.inspect()

        assert len(refs) == 4  # 2 years * 2 months

        # Verify partitions are correctly extracted
        partition_combos = {(ref.partitions["year"], ref.partitions["month"]) for ref in refs}
        expected_combos = {
            ("2023", "01"),
            ("2023", "02"),
            ("2024", "01"),
            ("2024", "02"),
        }
        assert partition_combos == expected_combos

        # Verify refs are stored in the domain
        assert asset.domain.refs == refs

    def test_inspect_nested_partitions(self, tmp_path: Path):
        """Test inspect with deeply nested partition structure."""
        # Create 3-level partition structure
        path = tmp_path / "year=2024" / "month=03" / "day=15"
        path.mkdir(parents=True)
        (path / "transactions.csv").write_text("transaction data")

        asset = LocalAsset(
            name="transactions",
            path=str(tmp_path),
            kind=AssetKind.CSV,
            platform=Platform.LOCAL,
            partitions=["year", "month", "day"],
        )

        refs = asset.inspect()

        assert len(refs) == 1
        assert refs[0].name == "transactions.csv"
        assert refs[0].partitions == {"year": "2024", "month": "03", "day": "15"}

    def test_inspect_multiple_files_in_partition(self, tmp_path: Path):
        """Test inspect with multiple files in same partition."""
        partition_dir = tmp_path / "year=2024"
        partition_dir.mkdir()

        # Create multiple files
        for i in range(5):
            (partition_dir / f"part_{i}.parquet").write_text(f"data {i}")

        asset = LocalAsset(
            name="multi_file",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["year"],
        )

        refs = asset.inspect()

        assert len(refs) == 5
        assert all(ref.partitions == {"year": "2024"} for ref in refs)
        assert set(ref.name for ref in refs) == {f"part_{i}.parquet" for i in range(5)}

    def test_inspect_preserves_uri_format(self, tmp_path: Path):
        """Test that inspect returns absolute URIs."""
        (tmp_path / "test.parquet").write_text("data")

        asset = LocalAsset(
            name="test",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        refs = asset.inspect()

        assert len(refs) == 1
        assert Path(refs[0].uri).is_absolute()
        assert refs[0].uri == str(tmp_path / "test.parquet")

    def test_inspect_updates_domain_refs(self, tmp_path: Path):
        """Test that inspect updates the domain model's refs."""
        (tmp_path / "file1.csv").write_text("data1")
        (tmp_path / "file2.csv").write_text("data2")

        asset = LocalAsset(
            name="test",
            path=str(tmp_path),
            kind=AssetKind.CSV,
            platform=Platform.LOCAL,
        )

        # Initially no refs
        assert asset.domain.refs == []

        # After inspect, refs should be populated
        refs = asset.inspect()
        assert asset.domain.refs == refs
        assert len(asset.domain.refs) == 2

    def test_inspect_with_subdirectories(self, tmp_path: Path):
        """Test inspect finds files recursively including subdirectories."""
        # Create files in subdirectories
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.parquet").write_text("nested data")
        (tmp_path / "root.parquet").write_text("root data")

        asset = LocalAsset(
            name="test",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        refs = asset.inspect()

        # rglob finds files recursively, so both should be found
        assert len(refs) == 2
        file_names = {ref.name for ref in refs}
        assert file_names == {"root.parquet", "nested.parquet"}


# ============================================================================
# Integration Tests
# ============================================================================


class TestLocalAssetIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow_simple(self, tmp_path: Path):
        """Test complete workflow: create asset -> add files -> inspect."""
        # Create asset
        asset = LocalAsset(
            name="sales_data",
            path=str(tmp_path),
            kind=AssetKind.CSV,
            platform=Platform.LOCAL,
            description="Sales transaction data",
        )

        # Add some files
        (tmp_path / "sales_2024.csv").write_text("id,amount\n1,100\n2,200")
        (tmp_path / "sales_2023.csv").write_text("id,amount\n3,150")

        # Inspect
        refs = asset.inspect()

        # Validate
        assert len(refs) == 2
        assert asset.domain.description == "Sales transaction data"
        assert all(ref.size > 0 for ref in refs)

    def test_full_workflow_partitioned(self, tmp_path: Path):
        """Test complete workflow with partitioned data."""
        # Create asset with partitions
        asset = LocalAsset(
            name="events",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["year", "month"],
            owner="analytics_team",
        )

        # Create partitioned structure
        for year in ["2023", "2024"]:
            for month in ["01", "06", "12"]:
                dir_path = tmp_path / f"year={year}" / f"month={month}"
                dir_path.mkdir(parents=True)
                (dir_path / f"events_{year}{month}.parquet").write_bytes(b"binary data")

        # Inspect
        refs = asset.inspect()

        # Validate
        assert len(refs) == 6  # 2 years * 3 months
        assert asset.domain.owner == "analytics_team"

        # Check all partitions are present
        years = {ref.partitions["year"] for ref in refs}
        months = {ref.partitions["month"] for ref in refs}
        assert years == {"2023", "2024"}
        assert months == {"01", "06", "12"}

    def test_reinspect_updates_refs(self, tmp_path: Path):
        """Test that re-running inspect updates refs correctly."""
        asset = LocalAsset(
            name="dynamic",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        # First inspect - empty
        refs1 = asset.inspect()
        assert len(refs1) == 0

        # Add a file
        (tmp_path / "new_file.parquet").write_text("new data")

        # Second inspect - should find the new file
        refs2 = asset.inspect()
        assert len(refs2) == 1
        assert refs2[0].name == "new_file.parquet"

        # Domain refs should be updated
        assert asset.domain.refs == refs2


# ============================================================================
# Performance / Smoke Tests
# ============================================================================


class TestLocalAssetPerformance:
    """Performance and smoke tests to ensure reliability at scale."""

    def test_smoke_inspect_many_files(self, tmp_path: Path):
        """Smoke test: inspect directory with many files."""
        # Create a large number of files
        num_files = 1000

        for i in range(num_files):
            (tmp_path / f"file_{i:04d}.parquet").write_text(f"data {i}")

        asset = LocalAsset(
            name="large_dataset",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        # Time the inspection
        start_time = time.time()
        refs = asset.inspect()
        elapsed_time = time.time() - start_time

        # Assertions
        assert len(refs) == num_files
        assert elapsed_time < 5.0  # Should complete in under 5 seconds

        # Verify all refs have proper metadata
        assert all(ref.size > 0 for ref in refs)
        assert all(ref.modified_at is not None for ref in refs)

    def test_smoke_inspect_deep_partitions(self, tmp_path: Path):
        """Smoke test: inspect deeply partitioned structure."""
        # Create a complex partition structure
        # 3 years * 12 months * 4 weeks = 144 partitions
        num_partitions = 0

        for year in ["2022", "2023", "2024"]:
            for month in [f"{m:02d}" for m in range(1, 13)]:
                for week in ["01", "02", "03", "04"]:
                    dir_path = tmp_path / f"year={year}" / f"month={month}" / f"week={week}"
                    dir_path.mkdir(parents=True)

                    # Create 2 files per partition
                    (dir_path / "part_0.parquet").write_text(f"data-{year}-{month}-{week}-0")
                    (dir_path / "part_1.parquet").write_text(f"data-{year}-{month}-{week}-1")
                    num_partitions += 1

        asset = LocalAsset(
            name="deep_partitioned",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["year", "month", "week"],
        )

        # Time the inspection
        start_time = time.time()
        refs = asset.inspect()
        elapsed_time = time.time() - start_time

        # Assertions
        expected_files = num_partitions * 2  # 2 files per partition
        assert len(refs) == expected_files
        assert elapsed_time < 10.0  # Should complete in under 10 seconds

        # Verify partition extraction is correct
        unique_partitions = {
            (ref.partitions["year"], ref.partitions["month"], ref.partitions["week"])
            for ref in refs
        }
        assert len(unique_partitions) == num_partitions

    def test_smoke_inspect_mixed_content(self, tmp_path: Path):
        """Smoke test: inspect with mixed file types and structures."""
        # Create mixed content
        # 100 parquet files in root
        for i in range(100):
            (tmp_path / f"root_{i}.parquet").write_text(f"root data {i}")

        # 50 CSV files (should be ignored)
        for i in range(50):
            (tmp_path / f"other_{i}.csv").write_text(f"csv data {i}")

        # 100 parquet files in various partitions
        for year in ["2023", "2024"]:
            for month in [f"{m:02d}" for m in range(1, 6)]:
                dir_path = tmp_path / f"year={year}" / f"month={month}"
                dir_path.mkdir(parents=True, exist_ok=True)

                for i in range(10):
                    (dir_path / f"part_{i}.parquet").write_text(f"data-{year}-{month}-{i}")

        asset = LocalAsset(
            name="mixed",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["year", "month"],
        )

        # Time the inspection
        start_time = time.time()
        refs = asset.inspect()
        elapsed_time = time.time() - start_time

        # Assertions
        # Should find 100 (partitioned) files, not root files or CSV files
        assert len(refs) == 100  # 2 years * 5 months * 10 files
        assert elapsed_time < 5.0

        # Verify no CSV files
        assert all(ref.name.endswith(".parquet") for ref in refs)

        # Verify all found files have partitions
        assert all(ref.partitions.get("year") in ["2023", "2024"] for ref in refs)

    def test_performance_multiple_inspects(self, tmp_path: Path):
        """Test performance of multiple sequential inspects."""
        # Create test structure
        for i in range(100):
            (tmp_path / f"file_{i}.parquet").write_text(f"data {i}")

        asset = LocalAsset(
            name="multi_inspect",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        # Run inspect multiple times
        times = []
        for _ in range(5):
            start = time.time()
            refs = asset.inspect()
            elapsed = time.time() - start
            times.append(elapsed)

            assert len(refs) == 100

        # Performance should be consistent
        avg_time = sum(times) / len(times)
        assert avg_time < 1.0  # Average should be under 1 second

        # No single run should take more than 2x the average
        assert all(t < avg_time * 2 for t in times)

    def test_memory_efficiency_large_refs(self, tmp_path: Path):
        """Smoke test: verify memory efficiency with many refs."""
        # Create many files
        num_files = 500
        for i in range(num_files):
            (tmp_path / f"file_{i:04d}.csv").write_text(f"data,{i}\n" * 100)

        asset = LocalAsset(
            name="memory_test",
            path=str(tmp_path),
            kind=AssetKind.CSV,
            platform=Platform.LOCAL,
        )

        refs = asset.inspect()

        assert len(refs) == num_files

        # Verify all refs are properly formed
        for ref in refs:
            assert isinstance(ref, LocalAssetRef)
            assert ref.uri.endswith(".csv")
            assert ref.size > 0
            assert isinstance(ref.name, str)
            assert isinstance(ref.stem, str)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestLocalAssetEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_directory(self, tmp_path: Path):
        """Test inspect on empty directory."""
        asset = LocalAsset(
            name="empty",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        refs = asset.inspect()
        assert refs == []

    def test_path_with_spaces(self, tmp_path: Path):
        """Test handling paths with spaces."""
        space_dir = tmp_path / "my data folder"
        space_dir.mkdir()
        (space_dir / "file 1.parquet").write_text("data")

        asset = LocalAsset(
            name="spaces",
            path=str(space_dir),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        refs = asset.inspect()
        assert len(refs) == 1
        assert "file 1.parquet" in refs[0].name

    def test_unicode_filenames(self, tmp_path: Path):
        """Test handling unicode characters in filenames."""
        (tmp_path / "数据_2024.parquet").write_text("unicode data")

        asset = LocalAsset(
            name="unicode",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        refs = asset.inspect()
        assert len(refs) == 1
        assert "数据_2024.parquet" in refs[0].name

    def test_partition_with_equals_in_value(self, tmp_path: Path):
        """Test partition values containing equals sign."""
        # Note: This is an edge case that might not work in all systems
        # but we should handle it gracefully
        dir_path = tmp_path / "query=select=all"
        dir_path.mkdir()
        (dir_path / "data.parquet").write_text("data")

        asset = LocalAsset(
            name="complex",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
            partitions=["query"],
        )

        refs = asset.inspect()
        # Should handle gracefully even if parsing is imperfect
        assert len(refs) >= 0  # At minimum shouldn't crash

    def test_very_long_path(self, tmp_path: Path):
        """Test handling of very long file paths."""
        # Create a deeply nested structure
        deep_path = tmp_path
        for i in range(20):
            deep_path = deep_path / f"level_{i}"
        deep_path.mkdir(parents=True)
        (deep_path / "deep_file.parquet").write_text("deep data")

        asset = LocalAsset(
            name="deep",
            path=str(tmp_path),
            kind=AssetKind.PARQUET,
            platform=Platform.LOCAL,
        )

        refs = asset.inspect()
        assert len(refs) == 1

    def test_symlink_handling(self, tmp_path: Path):
        """Test that symlinks are followed (or handled appropriately)."""
        # Create a real file
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        (real_dir / "actual.parquet").write_text("real data")

        # Create a symlink
        link_dir = tmp_path / "link"
        try:
            link_dir.symlink_to(real_dir)

            asset = LocalAsset(
                name="symlink",
                path=str(tmp_path),
                kind=AssetKind.PARQUET,
                platform=Platform.LOCAL,
            )

            refs = asset.inspect()
            # Should find at least the real file
            assert len(refs) >= 1
        except OSError:
            # Symlinks might not be supported on some systems
            pytest.skip("Symlinks not supported on this system")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
