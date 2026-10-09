from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.assetfile import LocalAssetfile
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.local.identity import LocalIdentity


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestLocalAssetfileInit:
    def test_missing_path_raises_validation_error(self):
        with pytest.raises(ValidationError):
            LocalAssetfile(_authorized=True)

    def test_path_does_not_need_to_exist(self, tmp_path):
        _target = tmp_path / "does_not_exist.csv"
        assetfile = LocalAssetfile(path=_target, _authorized=True)
        assert assetfile.path == _target.resolve()

    def test_filesystem_and_platform_are_fixed(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "a.csv", _authorized=True)
        assert assetfile.filesystem == AssetFilesystem.LOCAL
        assert assetfile.platform == Platform.LOCAL

    def test_default_identity_is_local_identity_default(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "a.csv", _authorized=True)
        assert assetfile.identity.name == LocalIdentity.default().name

    def test_default_size_and_modified_at_are_none(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "a.csv", _authorized=True)
        assert assetfile.size is None
        assert assetfile.modified_at is None


class TestLocalAssetfileDeriveIdentity:
    def test_resolves_named_identity(self, tmp_path):
        _identity = LocalIdentity(name="registered_local_identity")
        GlobalIdentities.identities = {"registered_local_identity": _identity}
        assetfile = LocalAssetfile(
            path=tmp_path / "a.csv",
            identity="registered_local_identity",
            _authorized=True,
        )
        assert assetfile.identity is _identity

    def test_platform_mismatch_raises_value_error(self, tmp_path):
        _aliyun_identity = AliyunIdentity(name="an_aliyun_identity")
        GlobalIdentities.identities = {"an_aliyun_identity": _aliyun_identity}
        with pytest.raises(ValueError):
            LocalAssetfile(
                path=tmp_path / "a.csv",
                identity="an_aliyun_identity",
                _authorized=True,
            )


class TestLocalAssetfilePartitions:
    def test_explicit_partitions_are_kept_as_is(self, tmp_path):
        assetfile = LocalAssetfile(
            path=tmp_path / "a.csv",
            partitions={"year": "2024"},
            _authorized=True,
        )
        assert assetfile.partitions == {"year": "2024"}

    def test_partitions_are_not_derived_from_path(self, tmp_path):
        _target = tmp_path / "year=2024" / "month=01" / "data.csv"
        assetfile = LocalAssetfile(path=_target, _authorized=True)
        assert assetfile.partitions == {}

    def test_no_partition_segments_results_in_empty_dict(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "data.csv", _authorized=True)
        assert assetfile.partitions == {}


class TestLocalAssetfileDeriveFilekind:
    def test_known_extension_maps_to_filekind(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "data.parquet", _authorized=True)
        assert assetfile.filekind == AssetFileKind.PARQUET

    def test_unknown_extension_defaults_to_object(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "data.unknownext", _authorized=True)
        assert assetfile.filekind == AssetFileKind.OBJECT

    def test_no_extension_defaults_to_object(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "data", _authorized=True)
        assert assetfile.filekind == AssetFileKind.OBJECT

    def test_explicit_filekind_is_overridden_by_path_derived_value(self, tmp_path):
        # filekind is always re-derived from the path suffix, explicit value is not preserved
        assetfile = LocalAssetfile(
            path=tmp_path / "data.parquet",
            filekind=AssetFileKind.OBJECT,
            _authorized=True,
        )
        assert assetfile.filekind == AssetFileKind.PARQUET

    def test_tags_resync_with_derived_filekind(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "data.parquet", _authorized=True)
        assert assetfile.tags["filekind"] == AssetFileKind.PARQUET


class TestLocalAssetfileUriFrnStemExtensionName:
    def test_uri_returns_file_scheme_with_path(self, tmp_path):
        _target = tmp_path / "data.csv"
        assetfile = LocalAssetfile(path=_target, _authorized=True)
        assert assetfile.uri == f"file://{_target.resolve()}"

    def test_frn_includes_platform_and_path(self, tmp_path):
        _target = tmp_path / "data.csv"
        assetfile = LocalAssetfile(path=_target, _authorized=True)
        assert assetfile.frn == f"assetfile:platform={Platform.LOCAL}:path={_target.resolve()}"

    def test_stem_and_extension_and_name(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "data.csv", _authorized=True)
        assert assetfile.stem == "data"
        assert assetfile.extension == "csv"
        assert assetfile.name == "data.csv"


class TestLocalAssetfileWriteAndReadBytes:
    def test_write_bytes_creates_parent_directories(self, tmp_path):
        _target = tmp_path / "nested" / "dir" / "data.csv"
        assetfile = LocalAssetfile(path=_target, _authorized=True)
        assetfile.write_bytes(b"hello")
        assert _target.read_bytes() == b"hello"

    def test_read_bytes_returns_written_content(self, tmp_path):
        _target = tmp_path / "data.csv"
        assetfile = LocalAssetfile(path=_target, _authorized=True)
        assetfile.write_bytes(b"col1,col2\n1,2\n")
        assert assetfile.read_bytes() == b"col1,col2\n1,2\n"

    def test_read_bytes_missing_file_raises_file_not_found_error(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "missing.csv", _authorized=True)
        with pytest.raises(FileNotFoundError):
            assetfile.read_bytes()


class TestLocalAssetfileLoad:
    def test_load_refreshes_size_and_modified_at_from_disk(self, tmp_path):
        _target = tmp_path / "data.csv"
        _target.write_bytes(b"12345")
        assetfile = LocalAssetfile(path=_target, _authorized=True)
        assert assetfile.size is None
        assetfile.load()
        assert assetfile.size == 5
        assert assetfile.modified_at == pytest.approx(_target.stat().st_mtime)

    def test_load_updates_metadata_without_discarding_existing_keys(self, tmp_path):
        _target = tmp_path / "data.csv"
        _target.write_bytes(b"12345")
        assetfile = LocalAssetfile(
            path=_target,
            metadata={"custom": "value"},
            _authorized=True,
        )
        assetfile.load()
        assert assetfile.metadata["custom"] == "value"
        assert "st_size" in assetfile.metadata

    def test_load_missing_file_raises_file_not_found_error(self, tmp_path):
        assetfile = LocalAssetfile(path=tmp_path / "missing.csv", _authorized=True)
        with pytest.raises(FileNotFoundError):
            assetfile.load()
