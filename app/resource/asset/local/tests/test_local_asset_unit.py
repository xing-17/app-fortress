from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.asset import LocalAsset
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.identity.local.local import LocalIdentity


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestLocalAssetInit:
    def test_missing_path_raises_validation_error(self):
        with pytest.raises(ValidationError):
            LocalAsset()

    def test_default_identity_is_local_identity_default(self, tmp_path):
        asset = LocalAsset(path=str(tmp_path))
        assert asset.identity.name == LocalIdentity.default().name

    def test_filesystem_and_platform_are_fixed(self, tmp_path):
        asset = LocalAsset(path=str(tmp_path))
        assert asset.filesystem == AssetFilesystem.LOCAL
        assert asset.platform == Platform.LOCAL

    def test_default_filekind_is_object(self, tmp_path):
        asset = LocalAsset(path=str(tmp_path))
        assert asset.filekind == AssetFileKind.OBJECT

    def test_default_partitions_is_empty_list(self, tmp_path):
        asset = LocalAsset(path=str(tmp_path))
        assert asset.partitions == []


class TestLocalAssetDerivePath:
    def test_string_path_is_resolved_to_path_and_created(self, tmp_path):
        _target = tmp_path / "new_asset_dir"
        asset = LocalAsset(path=str(_target))
        assert isinstance(asset.path, Path)
        assert asset.path == _target
        assert _target.is_dir()

    def test_existing_directory_string_path_is_kept(self, tmp_path):
        asset = LocalAsset(path=str(tmp_path))
        assert asset.path == tmp_path

    def test_string_path_pointing_to_file_raises_value_error(self, tmp_path):
        _file = tmp_path / "a_file.txt"
        _file.write_text("content")
        with pytest.raises(ValueError):
            LocalAsset(path=str(_file))


class TestLocalAssetDeriveIdentity:
    def test_resolves_named_identity(self, tmp_path):
        _identity = LocalIdentity(name="registered_local_identity")
        GlobalIdentities.identities = {"registered_local_identity": _identity}
        asset = LocalAsset(path=str(tmp_path), identity="registered_local_identity")
        assert asset.identity is _identity

    def test_platform_mismatch_raises_value_error(self, tmp_path):
        _aliyun_identity = AliyunIdentity(name="an_aliyun_identity")
        GlobalIdentities.identities = {"an_aliyun_identity": _aliyun_identity}
        with pytest.raises(ValueError):
            LocalAsset(path=str(tmp_path), identity="an_aliyun_identity")


class TestLocalAssetUri:
    def test_uri_returns_file_scheme_with_path(self, tmp_path):
        asset = LocalAsset(path=str(tmp_path))
        assert asset.uri == f"file://{tmp_path}"


class TestLocalAssetFrn:
    def test_frn_returns_local_asset_identifier(self, tmp_path):
        asset = LocalAsset(path=str(tmp_path))
        assert asset.frn == f"asset:{Platform.LOCAL}:{tmp_path}"


class TestLocalAssetTags:
    def test_tags_always_include_platform_filesystem_filekind(self, tmp_path):
        asset = LocalAsset(path=str(tmp_path), tags={"env": "prod"})
        assert asset.tags == {
            "env": "prod",
            "platform": Platform.LOCAL,
            "filesystem": AssetFilesystem.LOCAL,
            "filekind": AssetFileKind.OBJECT,
        }


class TestLocalAssetExport:
    def test_export_includes_identity_name(self, tmp_path):
        asset = LocalAsset(path=str(tmp_path))
        assert asset.export()["identity"] == LocalIdentity.default().name
