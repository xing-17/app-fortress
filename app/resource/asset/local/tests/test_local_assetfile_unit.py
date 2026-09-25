from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.assetfile import LocalAssetfile
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.identity.local.local import LocalIdentity


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestLocalAssetfileInit:
    def test_missing_path_raises_validation_error(self):
        with pytest.raises(ValidationError):
            LocalAssetfile()

    def test_default_identity_is_local_identity_default(self, tmp_path):
        assetfile = LocalAssetfile(path=str(tmp_path / "report.csv"))
        assert assetfile.identity.name == LocalIdentity.default().name

    def test_filesystem_and_platform_are_fixed(self, tmp_path):
        assetfile = LocalAssetfile(path=str(tmp_path / "report.csv"))
        assert assetfile.filesystem == AssetFilesystem.LOCAL
        assert assetfile.platform == Platform.LOCAL

    def test_default_filekind_is_object(self, tmp_path):
        assetfile = LocalAssetfile(path=str(tmp_path / "report.unknownext"))
        assert assetfile.filekind == AssetFileKind.OBJECT

    def test_default_partitions_is_empty_dict(self, tmp_path):
        assetfile = LocalAssetfile(path=str(tmp_path / "report.csv"))
        assert assetfile.partitions == {}


class TestLocalAssetfileValidatePath:
    def test_string_path_is_resolved_to_path(self, tmp_path):
        _target = tmp_path / "report.csv"
        assetfile = LocalAssetfile(path=str(_target))
        assert isinstance(assetfile.path, Path)
        assert assetfile.path == _target

    def test_nonexistent_path_does_not_raise(self, tmp_path):
        _target = tmp_path / "does" / "not" / "exist.csv"
        assetfile = LocalAssetfile(path=str(_target))
        assert assetfile.path == _target


class TestLocalAssetfileDeriveIdentity:
    def test_resolves_named_identity(self, tmp_path):
        _identity = LocalIdentity(name="registered_local_identity")
        GlobalIdentities.identities = {"registered_local_identity": _identity}
        assetfile = LocalAssetfile(path=str(tmp_path / "report.csv"), identity="registered_local_identity")
        assert assetfile.identity is _identity

    def test_platform_mismatch_raises_value_error(self, tmp_path):
        _aliyun_identity = AliyunIdentity(name="an_aliyun_identity")
        GlobalIdentities.identities = {"an_aliyun_identity": _aliyun_identity}
        with pytest.raises(ValueError):
            LocalAssetfile(path=str(tmp_path / "report.csv"), identity="an_aliyun_identity")


class TestLocalAssetfileDerivePartitions:
    def test_partitions_are_parsed_from_path_segments(self, tmp_path):
        _target = tmp_path / "dt=2024-01-01" / "report.csv"
        assetfile = LocalAssetfile(path=str(_target))
        assert assetfile.partitions == {"dt": "2024-01-01"}


class TestLocalAssetfileDeriveFilekind:
    def test_known_extension_resolves_to_matching_filekind(self, tmp_path):
        assetfile = LocalAssetfile(path=str(tmp_path / "report.parquet"))
        assert assetfile.filekind == AssetFileKind.PARQUET

    def test_unknown_extension_falls_back_to_object(self, tmp_path):
        assetfile = LocalAssetfile(path=str(tmp_path / "report.unknownext"))
        assert assetfile.filekind == AssetFileKind.OBJECT


class TestLocalAssetfileProperties:
    def test_uri_returns_file_scheme_with_path(self, tmp_path):
        _target = tmp_path / "report.csv"
        assetfile = LocalAssetfile(path=str(_target))
        assert assetfile.uri == f"file://{_target}"

    def test_stem_extension_and_name(self, tmp_path):
        _target = tmp_path / "report.csv"
        assetfile = LocalAssetfile(path=str(_target))
        assert assetfile.stem == "report"
        assert assetfile.extension == "csv"
        assert assetfile.name == "report.csv"

    def test_frn_returns_local_assetfile_identifier(self, tmp_path):
        _target = tmp_path / "report.csv"
        assetfile = LocalAssetfile(path=str(_target))
        assert assetfile.frn == f"assetfile:{Platform.LOCAL}:{_target}"


class TestLocalAssetfileTags:
    def test_tags_reflect_derived_filekind(self, tmp_path):
        assetfile = LocalAssetfile(path=str(tmp_path / "report.parquet"), tags={"env": "prod"})
        assert assetfile.tags == {
            "env": "prod",
            "platform": Platform.LOCAL,
            "filesystem": AssetFilesystem.LOCAL,
            "filekind": AssetFileKind.PARQUET,
        }


class TestLocalAssetfileExport:
    def test_export_includes_identity_name(self, tmp_path):
        assetfile = LocalAssetfile(path=str(tmp_path / "report.csv"))
        assert assetfile.export()["identity"] == LocalIdentity.default().name
