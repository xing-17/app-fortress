from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.asset import LocalAsset
from app.resource.asset.local.assetfile import LocalAssetfile
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.local.identity import LocalIdentity


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestLocalAssetInit:
    def test_missing_path_raises_validation_error(self):
        with pytest.raises(ValidationError):
            LocalAsset(_authorized=True)

    def test_path_is_created_when_missing(self, tmp_path):
        _target = tmp_path / "does_not_exist_yet"
        asset = LocalAsset(path=_target, _authorized=True)
        assert asset.path == _target.resolve()
        assert asset.path.is_dir()

    def test_path_pointing_to_a_file_raises_value_error(self, tmp_path):
        _file = tmp_path / "not_a_dir"
        _file.write_text("x")
        with pytest.raises(ValidationError):
            LocalAsset(path=_file, _authorized=True)

    def test_filesystem_and_platform_are_fixed(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        assert asset.filesystem == AssetFilesystem.LOCAL
        assert asset.platform == Platform.LOCAL

    def test_default_identity_is_local_identity_default(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        assert asset.identity.name == LocalIdentity.default().name

    def test_default_filekind_is_object(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        assert asset.filekind == AssetFileKind.OBJECT

    def test_default_partitions_is_empty_list(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        assert asset.partitions == []


class TestLocalAssetDeriveIdentity:
    def test_resolves_named_identity(self, tmp_path):
        _identity = LocalIdentity(name="registered_local_identity")
        GlobalIdentities.identities = {"registered_local_identity": _identity}
        asset = LocalAsset(path=tmp_path, identity="registered_local_identity", _authorized=True)
        assert asset.identity is _identity

    def test_platform_mismatch_raises_value_error(self, tmp_path):
        _aliyun_identity = AliyunIdentity(name="an_aliyun_identity")
        GlobalIdentities.identities = {"an_aliyun_identity": _aliyun_identity}
        with pytest.raises(ValueError):
            LocalAsset(path=tmp_path, identity="an_aliyun_identity", _authorized=True)


class TestLocalAssetUriFrnAndName:
    def test_uri_returns_file_scheme_with_path(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        assert asset.uri == f"file://{tmp_path.resolve()}"

    def test_frn_includes_platform_and_path(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        assert asset.frn == f"asset:platform={Platform.LOCAL}:path={tmp_path.resolve()}"

    def test_name_returns_directory_name(self, tmp_path):
        _target = tmp_path / "my_dataset"
        asset = LocalAsset(path=_target, _authorized=True)
        assert asset.name == "my_dataset"


class TestLocalAssetFullPattern:
    def test_without_partitions_has_no_partition_segment(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        assert asset.full_pattern == f"*{tmp_path.resolve()}/*"

    def test_with_partitions_includes_partition_segment(self, tmp_path):
        asset = LocalAsset(path=tmp_path, partitions=["year", "month"], _authorized=True)
        assert asset.full_pattern == f"*{tmp_path.resolve()}/year=*/month=*/*"

    def test_with_filekind_restricts_object_segment(self, tmp_path):
        asset = LocalAsset(path=tmp_path, filekind=AssetFileKind.PARQUET, _authorized=True)
        assert asset.full_pattern == f"*{tmp_path.resolve()}/*.parquet"


class TestLocalAssetListObjects:
    def test_missing_directory_returns_empty_list(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        # delete the directory after construction (eager mkdir already happened)
        tmp_path.rmdir()
        assert asset.list_objects() == []

    def test_empty_directory_returns_empty_list(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        assert asset.list_objects() == []

    def test_builds_assetfile_for_each_file(self, tmp_path):
        (tmp_path / "a.csv").write_bytes(b"1,2")
        (tmp_path / "b.csv").write_bytes(b"3,4")
        asset = LocalAsset(path=tmp_path, _authorized=True)
        _files = asset.list_objects()
        assert len(_files) == 2
        assert all(isinstance(f, LocalAssetfile) for f in _files)
        assert {f.name for f in _files} == {"a.csv", "b.csv"}

    def test_recursive_default_finds_nested_files(self, tmp_path):
        _nested = tmp_path / "year=2024"
        _nested.mkdir()
        (_nested / "data.csv").write_bytes(b"x")
        asset = LocalAsset(path=tmp_path, _authorized=True)
        _files = asset.list_objects()
        assert len(_files) == 1
        assert _files[0].name == "data.csv"

    def test_recursive_false_only_lists_direct_children(self, tmp_path):
        _nested = tmp_path / "year=2024"
        _nested.mkdir()
        (_nested / "data.csv").write_bytes(b"x")
        (tmp_path / "top.csv").write_bytes(b"y")
        asset = LocalAsset(path=tmp_path, _authorized=True)
        _files = asset.list_objects(recursive=False)
        assert {f.name for f in _files} == {"top.csv"}

    def test_assetfile_inherits_asset_identity_and_tags(self, tmp_path):
        (tmp_path / "a.csv").write_bytes(b"1")
        asset = LocalAsset(path=tmp_path, tags={"env": "prod"}, _authorized=True)
        _file = asset.list_objects()[0]
        assert _file.identity is asset.identity
        assert _file.tags["env"] == "prod"

    def test_assetfile_size_and_modified_at_come_from_stat(self, tmp_path):
        _f = tmp_path / "a.csv"
        _f.write_bytes(b"12345")
        asset = LocalAsset(path=tmp_path, _authorized=True)
        _file = asset.list_objects()[0]
        assert _file.size == 5
        assert _file.modified_at == pytest.approx(_f.stat().st_mtime)

    def test_metadata_excludes_none_values(self, tmp_path):
        (tmp_path / "a.csv").write_bytes(b"1")
        asset = LocalAsset(path=tmp_path, _authorized=True)
        _file = asset.list_objects()[0]
        assert all(v is not None for v in _file.metadata.values())


class TestLocalAssetListAssetfiles:
    def test_uses_full_pattern_and_matches_files(self, tmp_path):
        (tmp_path / "a.csv").write_bytes(b"1")
        asset = LocalAsset(path=tmp_path, _authorized=True)
        _files = asset.list_assetfiles()
        assert len(_files) == 1
        assert _files[0].name == "a.csv"

    def test_filekind_restricts_matched_files(self, tmp_path):
        (tmp_path / "a.parquet").write_bytes(b"1")
        (tmp_path / "b.csv").write_bytes(b"1")
        asset = LocalAsset(path=tmp_path, filekind=AssetFileKind.PARQUET, _authorized=True)
        _files = asset.list_assetfiles()
        assert {f.name for f in _files} == {"a.parquet"}

    def test_recursive_false_forwards_to_list_objects(self, tmp_path):
        _nested = tmp_path / "year=2024"
        _nested.mkdir()
        (_nested / "data.csv").write_bytes(b"x")
        asset = LocalAsset(path=tmp_path, _authorized=True)
        assert asset.list_assetfiles(recursive=False) == []

    def test_since_and_until_filter_by_modified_time(self, tmp_path):
        (tmp_path / "a.csv").write_bytes(b"1")
        asset = LocalAsset(path=tmp_path, _authorized=True)
        assert asset.list_assetfiles(since=9_999_999_999.0) == []
        assert len(asset.list_assetfiles(until=9_999_999_999.0)) == 1


class TestLocalAssetAssetfile:
    def test_creates_assetfile_without_partitions(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        _assetfile = asset.assetfile("data.csv")
        assert isinstance(_assetfile, LocalAssetfile)
        assert _assetfile.path == tmp_path.resolve() / "data.csv"

    def test_creates_assetfile_with_partitions(self, tmp_path):
        asset = LocalAsset(path=tmp_path, partitions=["year", "month"], _authorized=True)
        _assetfile = asset.assetfile("data.csv", partitions={"year": "2024", "month": "01"})
        assert _assetfile.path == tmp_path.resolve() / "year=2024/month=01/data.csv"

    def test_mismatched_partition_keys_raise_value_error(self, tmp_path):
        asset = LocalAsset(path=tmp_path, partitions=["year"], _authorized=True)
        with pytest.raises(ValueError):
            asset.assetfile("data.csv", partitions={"month": "01"})

    def test_missing_required_partitions_raise_value_error(self, tmp_path):
        asset = LocalAsset(path=tmp_path, partitions=["year"], _authorized=True)
        with pytest.raises(ValueError):
            asset.assetfile("data.csv")

    def test_assetfile_inherits_asset_identity_and_tags(self, tmp_path):
        asset = LocalAsset(path=tmp_path, tags={"env": "prod"}, _authorized=True)
        _assetfile = asset.assetfile("data.csv")
        assert _assetfile.identity is asset.identity
        assert _assetfile.tags["env"] == "prod"

    def test_filekind_mismatch_raises_value_error(self, tmp_path):
        asset = LocalAsset(path=tmp_path, filekind=AssetFileKind.PARQUET, _authorized=True)
        with pytest.raises(ValueError):
            asset.assetfile("data.csv")

    def test_filekind_match_succeeds(self, tmp_path):
        asset = LocalAsset(path=tmp_path, filekind=AssetFileKind.PARQUET, _authorized=True)
        _assetfile = asset.assetfile("data.parquet")
        assert _assetfile.filekind == AssetFileKind.PARQUET

    def test_path_escaping_asset_raises_value_error(self, tmp_path):
        asset = LocalAsset(path=tmp_path, _authorized=True)
        with pytest.raises(ValueError):
            asset.assetfile("../escape.csv")
