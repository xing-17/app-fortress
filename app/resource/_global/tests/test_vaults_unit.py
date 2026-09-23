from __future__ import annotations

import pytest

from app.resource._global.setting import GlobalSetting
from app.resource._global.vaults import GlobalVaults
from app.resource.asset._common._factory import VaultFactory
from app.resource.asset.local.vault import LocalVault
from app.resource.asset.oss.vault import OSSVault
from app.setting._vault import LocalVaultSetting, OSSVaultSetting
from app.setting.system import SystemSetting


def _patch_system(monkeypatch, *vaults) -> SystemSetting:
    _setting = SystemSetting(vaults=list(vaults))
    monkeypatch.setattr(GlobalSetting, "get_system", classmethod(lambda cls: _setting))
    return _setting


def _local_setting(name: str, tmp_path) -> LocalVaultSetting:
    return LocalVaultSetting(name=name, path=str(tmp_path), tags={})


def _oss_setting(name: str) -> OSSVaultSetting:
    return OSSVaultSetting(name=name, bucket="my-bucket", region="cn-hangzhou", tags={})


class TestGlobalVaultsLoad:
    def test_load_builds_instances_from_system_setting(self, monkeypatch, tmp_path):
        _patch_system(
            monkeypatch,
            _local_setting("local_one", tmp_path),
            _oss_setting("oss_one"),
        )
        GlobalVaults.load()
        assert set(GlobalVaults.vaults) == {"local_one", "oss_one"}
        assert isinstance(GlobalVaults.vaults["local_one"], LocalVault)
        assert isinstance(GlobalVaults.vaults["oss_one"], OSSVault)

    def test_load_raises_value_error_on_duplicate_names(self, monkeypatch, tmp_path):
        _patch_system(
            monkeypatch,
            _local_setting("dup", tmp_path),
            _local_setting("dup", tmp_path),
        )
        with pytest.raises(ValueError, match="Duplicate vault entry"):
            GlobalVaults.load()

    def test_load_wraps_factory_errors_in_value_error(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("broken", tmp_path))

        def _raise(cls, setting):
            raise RuntimeError("boom")

        monkeypatch.setattr(VaultFactory, "load", classmethod(_raise))
        with pytest.raises(ValueError, match="Failed to load vault 'broken'"):
            GlobalVaults.load()


class TestGlobalVaultsEnsureLoaded:
    def test_get_vault_lazy_loads_when_not_loaded(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("lazy_local", tmp_path))
        result = GlobalVaults.get_vault("lazy_local")
        assert isinstance(result, LocalVault)

    def test_get_vault_does_not_reload_when_already_cached(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("cached_local", tmp_path))
        GlobalVaults.load()

        def _fail_load(cls):
            raise AssertionError("load should not be called again")

        monkeypatch.setattr(GlobalVaults, "load", classmethod(_fail_load))
        result = GlobalVaults.get_vault("cached_local")
        assert result.name == "cached_local"

    def test_get_vault_raises_when_not_found(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("only_one", tmp_path))
        with pytest.raises(ValueError, match="Vault 'missing' not found"):
            GlobalVaults.get_vault("missing")
