from __future__ import annotations

import pytest

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._factory import VaultFactory
from app.resource.asset._common._vault import BaseVault
from app.resource.asset.local.vault import LocalVault
from app.resource.asset.oss.vault import OSSVault
from app.setting._vault import LocalVaultSetting, OSSVaultSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestVaultFactoryGet:
    def test_get_local_returns_local_vault_class(self):
        klass = VaultFactory.get(AssetFilesystem.LOCAL)
        assert klass is LocalVault

    def test_get_oss_returns_oss_vault_class(self):
        klass = VaultFactory.get(AssetFilesystem.OSS)
        assert klass is OSSVault

    def test_get_returned_class_is_subclass_of_base_vault(self):
        klass = VaultFactory.get(AssetFilesystem.OSS)
        assert issubclass(klass, BaseVault)

    def test_get_unknown_filesystem_raises_value_error(self):
        with pytest.raises(ValueError):
            VaultFactory.get("not_a_filesystem")


class TestVaultFactoryRegistryValidation:
    def test_get_raises_type_error_when_target_is_not_a_class(self, monkeypatch):
        monkeypatch.setitem(VaultFactory._registry, "not_a_class", "os:getcwd")
        with pytest.raises(TypeError):
            VaultFactory.get("not_a_class")

    def test_get_raises_type_error_when_target_is_not_base_vault_subclass(self, monkeypatch):
        monkeypatch.setitem(
            VaultFactory._registry,
            "not_base_vault",
            "app.resource.asset._common._factory:VaultFactory",
        )
        with pytest.raises(TypeError):
            VaultFactory.get("not_base_vault")


class TestVaultFactoryLoad:
    def test_load_returns_local_vault_instance(self, tmp_path):
        setting = LocalVaultSetting(name="my_vault", path=str(tmp_path))
        vault = VaultFactory.load(setting)
        assert isinstance(vault, LocalVault)
        assert vault.name == "my_vault"

    def test_load_returns_oss_vault_instance(self):
        setting = OSSVaultSetting(name="my_vault", bucket="my-bucket", region="cn-hangzhou")
        vault = VaultFactory.load(setting)
        assert isinstance(vault, OSSVault)
        assert vault.name == "my_vault"
        assert vault.bucket == "my-bucket"

    def test_load_raises_value_error_when_get_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr(VaultFactory, "get", classmethod(lambda cls, filesystem: None))
        setting = LocalVaultSetting(name="my_vault", path=str(tmp_path))
        with pytest.raises(ValueError):
            VaultFactory.load(setting)
