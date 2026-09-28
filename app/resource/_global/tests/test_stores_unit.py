from __future__ import annotations

import threading

import pytest

from app.internal.constant.platform import Platform
from app.resource._global.setting import GlobalSetting
from app.resource._global.stores import GlobalStores
from app.resource.store._common._factory import StoreFactory
from app.resource.store.aliyun.ots import OtsStore
from app.resource.store.local.duckdb import DuckDbStore
from app.setting._store import AliyunStoreSetting, LocalStoreSetting
from app.setting.system import SystemSetting


def _patch_system(monkeypatch, *stores) -> SystemSetting:
    _setting = SystemSetting(stores=list(stores))
    monkeypatch.setattr(GlobalSetting, "get_system", classmethod(lambda cls: _setting))
    return _setting


def _local_setting(name: str, tmp_path) -> LocalStoreSetting:
    return LocalStoreSetting(name=name, path=str(tmp_path), tags={})


def _aliyun_setting(name: str) -> AliyunStoreSetting:
    return AliyunStoreSetting(name=name, instance="my-instance", region="cn-hangzhou", tags={})


class TestGlobalStoresLoad:
    def test_load_builds_instances_from_system_setting(self, monkeypatch, tmp_path):
        _patch_system(
            monkeypatch,
            _local_setting("local_one", tmp_path),
            _aliyun_setting("aliyun_one"),
        )
        GlobalStores.load()
        assert set(GlobalStores.stores) == {"local_one", "aliyun_one"}
        assert isinstance(GlobalStores.stores["local_one"], DuckDbStore)
        assert isinstance(GlobalStores.stores["aliyun_one"], OtsStore)

    def test_load_raises_value_error_on_duplicate_names(self, monkeypatch, tmp_path):
        _patch_system(
            monkeypatch,
            _local_setting("dup", tmp_path),
            _local_setting("dup", tmp_path),
        )
        with pytest.raises(ValueError, match="Duplicate store entry"):
            GlobalStores.load()

    def test_load_wraps_factory_errors_in_value_error(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("broken", tmp_path))

        def _raise(cls, setting):
            raise RuntimeError("boom")

        monkeypatch.setattr(StoreFactory, "load", classmethod(_raise))
        with pytest.raises(ValueError, match="Failed to load store 'broken'"):
            GlobalStores.load()


class TestGlobalStoresEnsureLoaded:
    def test_get_store_lazy_loads_when_not_loaded(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("lazy_local", tmp_path))
        result = GlobalStores.get_store("lazy_local")
        assert isinstance(result, DuckDbStore)

    def test_get_store_does_not_reload_when_already_cached(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("cached_local", tmp_path))
        GlobalStores.load()

        def _fail_load(cls):
            raise AssertionError("load should not be called again")

        monkeypatch.setattr(GlobalStores, "load", classmethod(_fail_load))
        result = GlobalStores.get_store("cached_local")
        assert result.name == "cached_local"


class TestGlobalStoresGetStore:
    def test_get_store_raises_value_error_for_missing(self, monkeypatch):
        _patch_system(monkeypatch)
        with pytest.raises(ValueError, match="not found"):
            GlobalStores.get_store("missing")

    def test_get_store_returns_matching_instance(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("found", tmp_path))
        result = GlobalStores.get_store("found")
        assert result.name == "found"


class TestGlobalStoresResolve:
    def test_resolve_returns_instance_directly_without_registering(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        GlobalStores.load()
        _store = DuckDbStore(name="adhoc", path=str(tmp_path))
        result = GlobalStores.resolve(value=_store, default=_store)
        assert result is _store
        assert "adhoc" not in GlobalStores.stores

    def test_resolve_uses_default_without_registering_when_value_is_none(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        GlobalStores.load()
        _default = DuckDbStore(name="fallback", path=str(tmp_path))
        result = GlobalStores.resolve(value=None, default=_default)
        assert result is _default
        assert "fallback" not in GlobalStores.stores

    def test_resolve_raises_when_default_has_wrong_type(self, monkeypatch):
        _patch_system(monkeypatch)
        with pytest.raises(ValueError, match="Default must be type 'BaseStore'"):
            GlobalStores.resolve(value=None, default="not_a_store")

    def test_resolve_looks_up_by_name_when_value_is_string(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("registered", tmp_path))
        _default = DuckDbStore(name="fallback", path=str(tmp_path))
        result = GlobalStores.resolve(value="registered", default=_default)
        assert result is GlobalStores.stores["registered"]

    def test_resolve_raises_for_unsupported_type(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        _default = DuckDbStore(name="fallback", path=str(tmp_path))
        with pytest.raises(ValueError, match="Unsupported type"):
            GlobalStores.resolve(value=123, default=_default)

    def test_resolve_raises_when_platform_mismatch(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        _store = DuckDbStore(name="adhoc", path=str(tmp_path))
        with pytest.raises(ValueError, match="does not match platform"):
            GlobalStores.resolve(value=_store, default=_store, platform=Platform.ALIYUN)

    def test_resolve_passes_when_platform_matches(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        _store = DuckDbStore(name="adhoc", path=str(tmp_path))
        result = GlobalStores.resolve(value=_store, default=_store, platform=Platform.LOCAL)
        assert result is _store


class TestGlobalStoresListStoreNames:
    def test_list_store_names_returns_all_names(self, monkeypatch, tmp_path):
        _patch_system(
            monkeypatch,
            _local_setting("a", tmp_path),
            _aliyun_setting("b"),
        )
        assert set(GlobalStores.list_store_names()) == {"a", "b"}

    def test_list_store_names_filters_by_platform(self, monkeypatch, tmp_path):
        _patch_system(
            monkeypatch,
            _local_setting("a", tmp_path),
            _aliyun_setting("b"),
        )
        assert GlobalStores.list_store_names(platform=Platform.ALIYUN) == ["b"]


class TestGlobalStoresListStores:
    def test_list_stores_returns_all_instances(self, monkeypatch, tmp_path):
        _patch_system(
            monkeypatch,
            _local_setting("a", tmp_path),
            _aliyun_setting("b"),
        )
        result = GlobalStores.list_stores()
        assert {s.name for s in result} == {"a", "b"}

    def test_list_stores_filters_by_platform(self, monkeypatch, tmp_path):
        _patch_system(
            monkeypatch,
            _local_setting("a", tmp_path),
            _aliyun_setting("b"),
        )
        result = GlobalStores.list_stores(platform=Platform.LOCAL)
        assert len(result) == 1
        assert isinstance(result[0], DuckDbStore)

    def test_list_stores_returns_independent_snapshot(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("a", tmp_path))
        result = GlobalStores.list_stores()
        result.append(DuckDbStore(name="mutated", path=str(tmp_path)))
        assert len(GlobalStores.stores) == 1


class TestGlobalStoresReset:
    def test_reset_clears_cached_stores(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("a", tmp_path))
        GlobalStores.load()
        assert GlobalStores.stores is not None
        GlobalStores.reset()
        assert GlobalStores.stores is None


class TestGlobalStoresConcurrency:
    def test_get_store_under_concurrent_access_loads_only_once(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _local_setting("threaded", tmp_path))

        _original_load = StoreFactory.load
        _call_count = {"n": 0}

        def _counting_load(cls, setting):
            _call_count["n"] += 1
            return _original_load(setting)

        monkeypatch.setattr(StoreFactory, "load", classmethod(_counting_load))

        _results: list[DuckDbStore | None] = []
        _barrier = threading.Barrier(8)

        def _worker():
            _barrier.wait()
            _results.append(GlobalStores.get_store("threaded"))

        _threads = [threading.Thread(target=_worker) for _ in range(8)]
        for t in _threads:
            t.start()
        for t in _threads:
            t.join()

        assert _call_count["n"] == 1
        assert all(r is _results[0] for r in _results)
