from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.asset import LocalAsset
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
    def test_creates_default_path_when_not_specified(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        vault = LocalVault()
        assert vault.path == (tmp_path / "local" / "vault").resolve()
        assert vault.path.is_dir()

    def test_explicit_path_is_resolved_and_created(self, tmp_path):
        _target = tmp_path / "my_vault"
        vault = LocalVault(path=_target)
        assert vault.path == _target.resolve()
        assert vault.path.is_dir()

    def test_path_pointing_to_a_file_raises_value_error(self, tmp_path):
        _file = tmp_path / "not_a_dir"
        _file.write_text("x")
        with pytest.raises(ValidationError):
            LocalVault(path=_file)

    def test_filesystem_and_platform_are_fixed(self, tmp_path):
        vault = LocalVault(path=tmp_path)
        assert vault.filesystem == AssetFilesystem.LOCAL
        assert vault.platform == Platform.LOCAL

    def test_default_identity_is_local_identity_default(self, tmp_path):
        vault = LocalVault(path=tmp_path)
        assert vault.identity.name == LocalIdentity.default().name


class TestLocalVaultDeriveIdentity:
    def test_resolves_named_identity(self, tmp_path):
        _identity = LocalIdentity(name="registered_local_identity")
        GlobalIdentities.identities = {"registered_local_identity": _identity}
        vault = LocalVault(path=tmp_path, identity="registered_local_identity")
        assert vault.identity is _identity

    def test_platform_mismatch_raises_value_error(self, tmp_path):
        _aliyun_identity = AliyunIdentity(name="an_aliyun_identity")
        GlobalIdentities.identities = {"an_aliyun_identity": _aliyun_identity}
        with pytest.raises(ValueError):
            LocalVault(path=tmp_path, identity="an_aliyun_identity")


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
        assert vault.path == tmp_path.resolve()
        assert vault.description == "a local vault"
        assert vault.tags["env"] == "test"

    def test_from_setting_uses_default_identity_when_not_specified(self, tmp_path):
        setting = LocalVaultSetting(name="my_vault", path=str(tmp_path))
        vault = LocalVault.from_setting(setting)
        assert vault.identity.name == LocalIdentity.default().name

    def test_from_setting_resolves_named_identity(self, tmp_path):
        _identity = LocalIdentity(name="registered_local_identity")
        GlobalIdentities.identities = {"registered_local_identity": _identity}
        setting = LocalVaultSetting(name="my_vault", path=str(tmp_path), identity="registered_local_identity")
        vault = LocalVault.from_setting(setting)
        assert vault.identity is _identity


class TestLocalVaultUriAndFrn:
    def test_uri_returns_file_scheme_with_path(self, tmp_path):
        vault = LocalVault(path=tmp_path)
        assert vault.uri == f"file://{tmp_path.resolve()}"

    def test_frn_includes_platform_and_path(self, tmp_path):
        vault = LocalVault(path=tmp_path)
        assert vault.frn == f"vault:platform={Platform.LOCAL}:path={tmp_path.resolve()}"


class TestLocalVaultAsset:
    def test_asset_path_is_relative_to_vault(self, tmp_path):
        vault = LocalVault(path=tmp_path)
        asset = vault.asset("sub/dir")
        assert isinstance(asset, LocalAsset)
        assert asset.path == (tmp_path / "sub/dir").resolve()

    def test_asset_path_escaping_vault_raises_value_error(self, tmp_path):
        vault = LocalVault(path=tmp_path)
        with pytest.raises(ValueError):
            vault.asset("../escape")

    def test_asset_inherits_vault_identity(self, tmp_path):
        vault = LocalVault(path=tmp_path)
        asset = vault.asset("sub")
        assert asset.identity is vault.identity

    def test_asset_inherits_vault_tags(self, tmp_path):
        vault = LocalVault(path=tmp_path, tags={"env": "prod"})
        asset = vault.asset("sub")
        assert asset.tags["env"] == "prod"

    def test_asset_passes_through_filekind_and_partitions(self, tmp_path):
        vault = LocalVault(path=tmp_path)
        asset = vault.asset("sub", filekind=AssetFileKind.PARQUET, partitions=["year"])
        assert asset.filekind == AssetFileKind.PARQUET
        assert asset.partitions == ["year"]

    def test_asset_without_explicit_filekind_defaults_to_object(self, tmp_path):
        vault = LocalVault(path=tmp_path)
        asset = vault.asset("sub")
        assert asset.filekind == AssetFileKind.OBJECT
        assert asset.partitions == []
