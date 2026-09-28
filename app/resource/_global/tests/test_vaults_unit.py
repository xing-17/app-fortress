from __future__ import annotations

import threading

import pytest

from app.internal.constant.assetfilesystem import AssetFilesystem
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


class TestGlobalVaultsGetVault:
    def test_get_vault_raises_value_error_for_missing(self, monkeypatch):
        _patch_system(monkeypatch)
        with pytest.raises(ValueError, match="not found"):
            GlobalVaults.get_vault("missing")

    def test_get_vault_returns_none_for_missing_when_not_strict(self, monkeypatch):
        _patch_system(monkeypatch)
        assert GlobalVaults.get_vault("missing", strict=False) is None

    def test_get_vault_returns_matching_instance(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("found", tmp_path))
        result = GlobalVaults.get_vault("found")
        assert result.name == "found"


class TestGlobalVaultsResolve:
    def test_resolve_returns_instance_directly_without_registering(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        GlobalVaults.load()
        _vault = LocalVault(name="adhoc", path=str(tmp_path))
        result = GlobalVaults.resolve(value=_vault, default=_vault)
        assert result is _vault
        assert "adhoc" not in GlobalVaults.vaults

    def test_resolve_uses_default_without_registering_when_value_is_none(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        GlobalVaults.load()
        _default = LocalVault(name="fallback", path=str(tmp_path))
        result = GlobalVaults.resolve(value=None, default=_default)
        assert result is _default
        assert "fallback" not in GlobalVaults.vaults

    def test_resolve_raises_when_default_has_wrong_type(self, monkeypatch):
        _patch_system(monkeypatch)
        with pytest.raises(ValueError, match="Default must be type 'BaseVault'"):
            GlobalVaults.resolve(value=None, default="not_a_vault")

    def test_resolve_looks_up_by_name_when_value_is_string(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("registered", tmp_path))
        _default = LocalVault(name="fallback", path=str(tmp_path))
        result = GlobalVaults.resolve(value="registered", default=_default)
        assert result is GlobalVaults.vaults["registered"]

    def test_resolve_raises_for_unsupported_type(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        _default = LocalVault(name="fallback", path=str(tmp_path))
        with pytest.raises(ValueError, match="Unsupported type"):
            GlobalVaults.resolve(value=123, default=_default)

    def test_resolve_raises_when_filesystem_mismatch(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        _vault = LocalVault(name="adhoc", path=str(tmp_path))
        with pytest.raises(ValueError, match="does not match filesystem"):
            GlobalVaults.resolve(value=_vault, default=_vault, filesystem=AssetFilesystem.OSS)

    def test_resolve_passes_when_filesystem_matches(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        _vault = LocalVault(name="adhoc", path=str(tmp_path))
        result = GlobalVaults.resolve(value=_vault, default=_vault, filesystem=AssetFilesystem.LOCAL)
        assert result is _vault


class TestGlobalVaultsListVaultNames:
    def test_list_vault_names_returns_all_names(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("a", tmp_path), _oss_setting("b"))
        assert set(GlobalVaults.list_vault_names()) == {"a", "b"}

    def test_list_vault_names_filters_by_filesystem(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("a", tmp_path), _oss_setting("b"))
        assert GlobalVaults.list_vault_names(filesystem=AssetFilesystem.OSS) == ["b"]


class TestGlobalVaultsListVaults:
    def test_list_vaults_returns_all_instances(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("a", tmp_path), _oss_setting("b"))
        result = GlobalVaults.list_vaults()
        assert {v.name for v in result} == {"a", "b"}

    def test_list_vaults_filters_by_filesystem(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("a", tmp_path), _oss_setting("b"))
        result = GlobalVaults.list_vaults(filesystem=AssetFilesystem.LOCAL)
        assert len(result) == 1
        assert isinstance(result[0], LocalVault)

    def test_list_vaults_returns_independent_snapshot(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("a", tmp_path))
        result = GlobalVaults.list_vaults()
        result.append(LocalVault(name="mutated", path=str(tmp_path)))
        assert len(GlobalVaults.vaults) == 1


class TestGlobalVaultsReset:
    def test_reset_clears_cached_vaults(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("a", tmp_path))
        GlobalVaults.load()
        assert GlobalVaults.vaults is not None
        GlobalVaults.reset()
        assert GlobalVaults.vaults is None


class TestGlobalVaultsConcurrency:
    def test_get_vault_under_concurrent_access_loads_only_once(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("threaded", tmp_path))

        _original_load = VaultFactory.load
        _call_count = {"n": 0}

        def _counting_load(cls, setting):
            _call_count["n"] += 1
            return _original_load(setting)

        monkeypatch.setattr(VaultFactory, "load", classmethod(_counting_load))

        _results: list[LocalVault | None] = []
        _barrier = threading.Barrier(8)

        def _worker():
            _barrier.wait()
            _results.append(GlobalVaults.get_vault("threaded"))

        _threads = [threading.Thread(target=_worker) for _ in range(8)]
        for t in _threads:
            t.start()
        for t in _threads:
            t.join()

        assert _call_count["n"] == 1
        assert all(r is _results[0] for r in _results)
