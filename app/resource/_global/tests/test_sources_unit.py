from __future__ import annotations

import threading

import pytest

from app.internal.constant.sourceprovider import SourceProvider
from app.resource._global.setting import GlobalSetting
from app.resource._global.sources import GlobalSources
from app.resource.source._common._factory import SourceFactory
from app.resource.source.tushare import TushareSource
from app.setting._source import TushareSourceSetting
from app.setting._store import FileStoreSetting
from app.setting._vault import LocalVaultSetting
from app.setting.system import SystemSetting


def _patch_system(monkeypatch, *sources) -> SystemSetting:
    _setting = SystemSetting(sources=list(sources))
    monkeypatch.setattr(GlobalSetting, "get_system", classmethod(lambda cls: _setting))
    return _setting


def _tushare_setting(name: str, tmp_path) -> TushareSourceSetting:
    return TushareSourceSetting(
        name=name,
        key="k",
        vault=LocalVaultSetting(name=f"{name}_vault", path=str(tmp_path / name / "vault")),
        store=FileStoreSetting(name=f"{name}_store", path=str(tmp_path / name / "store")),
    )


def _tushare_source(name: str, tmp_path) -> TushareSource:
    return TushareSource.from_setting(_tushare_setting(name, tmp_path))


class TestGlobalSourcesLoad:
    def test_load_builds_instances_from_system_setting(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("one", tmp_path), _tushare_setting("two", tmp_path))
        GlobalSources.load()
        assert set(GlobalSources.sources) == {"one", "two"}
        assert isinstance(GlobalSources.sources["one"], TushareSource)

    def test_load_raises_value_error_on_duplicate_names(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("dup", tmp_path), _tushare_setting("dup", tmp_path))
        with pytest.raises(ValueError, match="Duplicate source entry"):
            GlobalSources.load()

    def test_load_wraps_factory_errors_in_value_error(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("broken", tmp_path))

        def _raise(cls, setting):
            raise RuntimeError("boom")

        monkeypatch.setattr(SourceFactory, "load", classmethod(_raise))
        with pytest.raises(ValueError, match="Failed to load source 'broken'"):
            GlobalSources.load()


class TestGlobalSourcesEnsureLoaded:
    def test_get_source_lazy_loads_when_not_loaded(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("lazy", tmp_path))
        assert isinstance(GlobalSources.get_source("lazy"), TushareSource)

    def test_get_source_does_not_reload_when_already_cached(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("cached", tmp_path))
        GlobalSources.load()

        def _fail_load(cls):
            raise AssertionError("load should not be called again")

        monkeypatch.setattr(GlobalSources, "load", classmethod(_fail_load))
        assert GlobalSources.get_source("cached").name == "cached"


class TestGlobalSourcesGetSource:
    def test_get_source_raises_value_error_for_missing(self, monkeypatch):
        _patch_system(monkeypatch)
        with pytest.raises(ValueError, match="not found"):
            GlobalSources.get_source("missing")

    def test_get_source_returns_none_for_missing_when_not_strict(self, monkeypatch):
        _patch_system(monkeypatch)
        assert GlobalSources.get_source("missing", strict=False) is None

    def test_get_source_returns_matching_instance(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("found", tmp_path))
        assert GlobalSources.get_source("found").name == "found"


class TestGlobalSourcesResolve:
    def test_resolve_returns_instance_directly_without_registering(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        GlobalSources.load()
        _source = _tushare_source("adhoc", tmp_path)
        assert GlobalSources.resolve(value=_source) is _source
        assert "adhoc" not in GlobalSources.sources

    def test_resolve_uses_default_without_registering_when_value_is_none(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        GlobalSources.load()
        _default = _tushare_source("fallback", tmp_path)
        assert GlobalSources.resolve(value=None, default=_default) is _default
        assert "fallback" not in GlobalSources.sources

    def test_resolve_raises_when_value_is_none_and_no_default(self, monkeypatch):
        _patch_system(monkeypatch)
        with pytest.raises(ValueError, match="no default provided"):
            GlobalSources.resolve(value=None)

    def test_resolve_raises_when_default_has_wrong_type(self, monkeypatch):
        _patch_system(monkeypatch)
        with pytest.raises(ValueError, match="Default must be type 'BaseSource'"):
            GlobalSources.resolve(value=None, default="not_a_source")

    def test_resolve_looks_up_by_name_when_value_is_string(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("registered", tmp_path))
        assert GlobalSources.resolve(value="registered") is GlobalSources.sources["registered"]

    def test_resolve_builds_from_setting_without_registering(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        GlobalSources.load()
        result = GlobalSources.resolve(value=_tushare_setting("from_setting", tmp_path))
        assert isinstance(result, TushareSource)
        assert "from_setting" not in GlobalSources.sources

    def test_resolve_raises_for_unsupported_type(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        _default = _tushare_source("fallback", tmp_path)
        with pytest.raises(ValueError, match="Unsupported type"):
            GlobalSources.resolve(value=123, default=_default)

    def test_resolve_raises_when_provider_mismatch(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        _source = _tushare_source("adhoc", tmp_path)
        with pytest.raises(ValueError, match="does not match provider"):
            GlobalSources.resolve(value=_source, provider=SourceProvider.ABS)

    def test_resolve_passes_when_provider_matches(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch)
        _source = _tushare_source("adhoc", tmp_path)
        assert GlobalSources.resolve(value=_source, provider=SourceProvider.TUSHARE) is _source


class TestGlobalSourcesListSourceNames:
    def test_list_source_names_returns_all_names(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("a", tmp_path), _tushare_setting("b", tmp_path))
        assert set(GlobalSources.list_source_names()) == {"a", "b"}

    def test_list_source_names_filters_by_provider(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("a", tmp_path))
        assert GlobalSources.list_source_names(provider=SourceProvider.TUSHARE) == ["a"]
        assert GlobalSources.list_source_names(provider=SourceProvider.ABS) == []


class TestGlobalSourcesListSources:
    def test_list_sources_returns_all_instances(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("a", tmp_path), _tushare_setting("b", tmp_path))
        assert {s.name for s in GlobalSources.list_sources()} == {"a", "b"}

    def test_list_sources_filters_by_provider(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("a", tmp_path))
        assert len(GlobalSources.list_sources(provider=SourceProvider.TUSHARE)) == 1
        assert GlobalSources.list_sources(provider=SourceProvider.NSW_VG) == []

    def test_list_sources_returns_independent_snapshot(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("a", tmp_path))
        result = GlobalSources.list_sources()
        result.append(_tushare_source("mutated", tmp_path))
        assert len(GlobalSources.sources) == 1


class TestGlobalSourcesReset:
    def test_reset_clears_cached_sources(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("a", tmp_path))
        GlobalSources.load()
        assert GlobalSources.sources is not None
        GlobalSources.reset()
        assert GlobalSources.sources is None


class TestGlobalSourcesConcurrency:
    def test_get_source_under_concurrent_access_loads_only_once(self, monkeypatch, tmp_path):
        _patch_system(monkeypatch, _tushare_setting("threaded", tmp_path))

        _original_load = SourceFactory.load
        _call_count = {"n": 0}

        def _counting_load(cls, setting):
            _call_count["n"] += 1
            return _original_load(setting)

        monkeypatch.setattr(SourceFactory, "load", classmethod(_counting_load))

        _results: list[TushareSource | None] = []
        _barrier = threading.Barrier(8)

        def _worker():
            _barrier.wait()
            _results.append(GlobalSources.get_source("threaded"))

        _threads = [threading.Thread(target=_worker) for _ in range(8)]
        for t in _threads:
            t.start()
        for t in _threads:
            t.join()

        assert _call_count["n"] == 1
        assert all(r is _results[0] for r in _results)
