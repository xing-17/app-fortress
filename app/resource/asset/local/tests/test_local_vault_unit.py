from __future__ import annotations

from pathlib import Path

import pytest

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.vault import LocalVault
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.local.identity import LocalIdentity
from app.setting._vault import LocalVaultSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestLocalVaultInit:
    def test_default_identity_is_local_identity_default(self, tmp_path):
        vault = LocalVault(path=str(tmp_path))
        assert vault.identity.name == LocalIdentity.default().name

    def test_filesystem_and_platform_are_fixed(self, tmp_path):
        vault = LocalVault(path=str(tmp_path))
        assert vault.filesystem == AssetFilesystem.LOCAL
        assert vault.platform == Platform.LOCAL


class TestLocalVaultDerivePath:
    def test_string_path_is_resolved_to_path_and_created(self, tmp_path):
        _target = tmp_path / "new_vault_dir"
        vault = LocalVault(path=str(_target))
        assert isinstance(vault.path, Path)
        assert vault.path == _target
        assert _target.is_dir()

    def test_existing_directory_string_path_is_kept(self, tmp_path):
        vault = LocalVault(path=str(tmp_path))
        assert vault.path == tmp_path

    def test_string_path_pointing_to_file_raises_value_error(self, tmp_path):
        _file = tmp_path / "a_file.txt"
        _file.write_text("content")
        with pytest.raises(ValueError):
            LocalVault(path=str(_file))


class TestLocalVaultFromSetting:
    def test_from_setting_copies_name_path_description_tags(self, tmp_path):
        setting = LocalVaultSetting(
            name="my_vault",
            path=str(tmp_path),
            description="a local vault",
            tags={"env": "test"},
        )
        vault = LocalVault.from_setting(setting)
        assert vault.name == "my_vault"
        assert vault.path == tmp_path
        assert vault.description == "a local vault"
        assert vault.tags["env"] == "test"

    def test_from_setting_uses_default_identity_when_not_specified(self, tmp_path):
        setting = LocalVaultSetting(name="my_vault", path=str(tmp_path))
        vault = LocalVault.from_setting(setting)
        assert vault.identity.name == LocalIdentity.default().name

    def test_from_setting_resolves_named_identity(self, tmp_path):
        _identity = LocalIdentity(name="registered_local_identity")
        GlobalIdentities.identities = {"registered_local_identity": _identity}
        setting = LocalVaultSetting(
            name="my_vault",
            path=str(tmp_path),
            identity="registered_local_identity",
        )
        vault = LocalVault.from_setting(setting)
        assert vault.identity is _identity

    def test_from_setting_raises_value_error_on_platform_mismatch(self, tmp_path):
        _aliyun_identity = AliyunIdentity(name="an_aliyun_identity")
        GlobalIdentities.identities = {"an_aliyun_identity": _aliyun_identity}
        setting = LocalVaultSetting(
            name="my_vault",
            path=str(tmp_path),
            identity="an_aliyun_identity",
        )
        with pytest.raises(ValueError):
            LocalVault.from_setting(setting)


class TestLocalVaultUri:
    def test_uri_returns_file_scheme_with_path(self, tmp_path):
        vault = LocalVault(path=str(tmp_path))
        assert vault.uri == f"file://{tmp_path}"


class TestLocalVaultAsset:
    def test_asset_path_is_subdirectory_of_vault_path(self, tmp_path):
        vault = LocalVault(path=str(tmp_path))
        asset = vault.asset("sub/dir")
        assert asset.path == tmp_path / "sub" / "dir"
        assert asset.path.is_dir()

    def test_asset_inherits_vault_identity(self, tmp_path):
        vault = LocalVault(path=str(tmp_path))
        asset = vault.asset("sub")
        assert asset.identity is vault.identity

    def test_asset_inherits_vault_tags(self, tmp_path):
        vault = LocalVault(path=str(tmp_path), tags={"env": "prod"})
        asset = vault.asset("sub")
        assert asset.tags["env"] == "prod"

    def test_asset_default_filekind_is_object(self, tmp_path):
        vault = LocalVault(path=str(tmp_path))
        asset = vault.asset("sub")
        assert asset.filekind == AssetFileKind.OBJECT

    def test_asset_passes_through_filekind_and_partitions(self, tmp_path):
        vault = LocalVault(path=str(tmp_path))
        asset = vault.asset("sub", filekind=AssetFileKind.PARQUET, partitions=["year=2024"])
        assert asset.filekind == AssetFileKind.PARQUET
        assert asset.partitions == ["year=2024"]

    def test_dot_dot_rel_raises_value_error(self, tmp_path):
        vault = LocalVault(path=str(tmp_path))
        with pytest.raises(ValueError):
            vault.asset("../escape")

    def test_absolute_rel_raises_value_error(self, tmp_path):
        vault = LocalVault(path=str(tmp_path))
        with pytest.raises(ValueError):
            vault.asset("/etc/passwd")
