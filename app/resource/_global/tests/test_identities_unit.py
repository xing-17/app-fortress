from __future__ import annotations

import threading

import pytest

from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource._global.setting import GlobalSetting
from app.resource.identity._common._factory import IdentityFactory
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.identity.local.local import LocalIdentity
from app.setting._identity import AliyunIdentitySetting, LocalIdentitySetting
from app.setting.system import SystemSetting


def _patch_system(monkeypatch, *identities) -> SystemSetting:
    _setting = SystemSetting(identities=list(identities))
    monkeypatch.setattr(GlobalSetting, "get_system", classmethod(lambda cls: _setting))
    return _setting


class TestGlobalIdentitiesLoad:
    def test_load_builds_instances_from_system_setting(self, monkeypatch):
        _patch_system(
            monkeypatch,
            LocalIdentitySetting(name="local_one", tags={"env": "test"}),
            AliyunIdentitySetting(name="aliyun_one", access_key_id="ak", access_key_secret="sk"),
        )
        GlobalIdentities.load()
        assert set(GlobalIdentities.identities) == {"local_one", "aliyun_one"}
        assert isinstance(GlobalIdentities.identities["local_one"], LocalIdentity)
        assert isinstance(GlobalIdentities.identities["aliyun_one"], AliyunIdentity)

    def test_load_raises_value_error_on_duplicate_names(self, monkeypatch):
        _patch_system(
            monkeypatch,
            LocalIdentitySetting(name="dup"),
            LocalIdentitySetting(name="dup"),
        )
        with pytest.raises(ValueError, match="Duplicate identity entry"):
            GlobalIdentities.load()

    def test_load_wraps_factory_errors_in_value_error(self, monkeypatch):
        _patch_system(monkeypatch, LocalIdentitySetting(name="broken"))

        def _raise(cls, setting):
            raise RuntimeError("boom")

        monkeypatch.setattr(IdentityFactory, "load", classmethod(_raise))
        with pytest.raises(ValueError, match="Failed to load identity 'broken'"):
            GlobalIdentities.load()


class TestGlobalIdentitiesEnsureLoaded:
    def test_get_identity_lazy_loads_when_not_loaded(self, monkeypatch):
        _patch_system(monkeypatch, LocalIdentitySetting(name="lazy_local"))
        result = GlobalIdentities.get_identity("lazy_local")
        assert isinstance(result, LocalIdentity)

    def test_get_identity_does_not_reload_when_already_cached(self, monkeypatch):
        _patch_system(monkeypatch, LocalIdentitySetting(name="cached_local"))
        GlobalIdentities.load()

        def _fail_load(cls):
            raise AssertionError("load should not be called again")

        monkeypatch.setattr(GlobalIdentities, "load", classmethod(_fail_load))
        result = GlobalIdentities.get_identity("cached_local")
        assert result.name == "cached_local"


class TestGlobalIdentitiesGetIdentity:
    def test_get_identity_returns_none_for_missing_when_not_strict(self, monkeypatch):
        _patch_system(monkeypatch)
        assert GlobalIdentities.get_identity("missing") is None

    def test_get_identity_raises_value_error_for_missing_when_strict(self, monkeypatch):
        _patch_system(monkeypatch)
        with pytest.raises(ValueError, match="not found"):
            GlobalIdentities.get_identity("missing", strict=True)

    def test_get_identity_returns_matching_instance(self, monkeypatch):
        _patch_system(monkeypatch, LocalIdentitySetting(name="found"))
        result = GlobalIdentities.get_identity("found")
        assert result is not None
        assert result.name == "found"


class TestGlobalIdentitiesResolve:
    def test_resolve_returns_instance_directly_without_registering(self, monkeypatch):
        _patch_system(monkeypatch)
        GlobalIdentities.load()
        _identity = LocalIdentity(name="adhoc")
        result = GlobalIdentities.resolve(value=_identity, default=_identity)
        assert result is _identity
        assert "adhoc" not in GlobalIdentities.identities

    def test_resolve_uses_default_without_registering_when_value_is_none(self, monkeypatch):
        _patch_system(monkeypatch)
        GlobalIdentities.load()
        _default = LocalIdentity(name="fallback")
        result = GlobalIdentities.resolve(value=None, default=_default)
        assert result is _default
        assert "fallback" not in GlobalIdentities.identities

    def test_resolve_raises_when_default_has_wrong_type(self, monkeypatch):
        _patch_system(monkeypatch)
        with pytest.raises(ValueError, match="Default must be type 'BaseIdentity'"):
            GlobalIdentities.resolve(value=None, default="not_an_identity")

    def test_resolve_looks_up_by_name_when_value_is_string(self, monkeypatch):
        _patch_system(monkeypatch, LocalIdentitySetting(name="registered"))
        _default = LocalIdentity(name="fallback")
        result = GlobalIdentities.resolve(value="registered", default=_default)
        assert result is GlobalIdentities.identities["registered"]

    def test_resolve_raises_for_unsupported_type(self, monkeypatch):
        _patch_system(monkeypatch)
        _default = LocalIdentity(name="fallback")
        with pytest.raises(ValueError, match="Unsupported type"):
            GlobalIdentities.resolve(value=123, default=_default)

    def test_resolve_raises_when_platform_mismatch(self, monkeypatch):
        _patch_system(monkeypatch)
        _identity = LocalIdentity(name="adhoc")
        with pytest.raises(ValueError, match="does not match platform"):
            GlobalIdentities.resolve(value=_identity, default=_identity, platform=Platform.ALIYUN)

    def test_resolve_passes_when_platform_matches(self, monkeypatch):
        _patch_system(monkeypatch)
        _identity = LocalIdentity(name="adhoc")
        result = GlobalIdentities.resolve(value=_identity, default=_identity, platform=Platform.LOCAL)
        assert result is _identity


class TestGlobalIdentitiesListIdentityNames:
    def test_list_identity_names_returns_all_names(self, monkeypatch):
        _patch_system(
            monkeypatch,
            LocalIdentitySetting(name="a"),
            AliyunIdentitySetting(name="b", access_key_id="x", access_key_secret="y"),
        )
        assert set(GlobalIdentities.list_identity_names()) == {"a", "b"}

    def test_list_identity_names_filters_by_platform(self, monkeypatch):
        _patch_system(
            monkeypatch,
            LocalIdentitySetting(name="a"),
            AliyunIdentitySetting(name="b", access_key_id="x", access_key_secret="y"),
        )
        assert GlobalIdentities.list_identity_names(platform=Platform.ALIYUN) == ["b"]


class TestGlobalIdentitiesListIdentities:
    def test_list_identities_returns_all_instances(self, monkeypatch):
        _patch_system(
            monkeypatch,
            LocalIdentitySetting(name="a"),
            AliyunIdentitySetting(name="b", access_key_id="x", access_key_secret="y"),
        )
        result = GlobalIdentities.list_identities()
        assert {i.name for i in result} == {"a", "b"}

    def test_list_identities_filters_by_platform(self, monkeypatch):
        _patch_system(
            monkeypatch,
            LocalIdentitySetting(name="a"),
            AliyunIdentitySetting(name="b", access_key_id="x", access_key_secret="y"),
        )
        result = GlobalIdentities.list_identities(platform=Platform.LOCAL)
        assert len(result) == 1
        assert isinstance(result[0], LocalIdentity)

    def test_list_identities_returns_independent_snapshot(self, monkeypatch):
        _patch_system(monkeypatch, LocalIdentitySetting(name="a"))
        result = GlobalIdentities.list_identities()
        result.append(LocalIdentity(name="mutated"))
        assert len(GlobalIdentities.identities) == 1


class TestGlobalIdentitiesReset:
    def test_reset_clears_cached_identities(self, monkeypatch):
        _patch_system(monkeypatch, LocalIdentitySetting(name="a"))
        GlobalIdentities.load()
        assert GlobalIdentities.identities is not None
        GlobalIdentities.reset()
        assert GlobalIdentities.identities is None


class TestGlobalIdentitiesConcurrency:
    def test_get_identity_under_concurrent_access_loads_only_once(self, monkeypatch):
        _patch_system(monkeypatch, LocalIdentitySetting(name="threaded"))

        _original_load = IdentityFactory.load
        _call_count = {"n": 0}

        def _counting_load(cls, setting):
            _call_count["n"] += 1
            return _original_load(setting)

        monkeypatch.setattr(IdentityFactory, "load", classmethod(_counting_load))

        _results: list[LocalIdentity | None] = []
        _barrier = threading.Barrier(8)

        def _worker():
            _barrier.wait()
            _results.append(GlobalIdentities.get_identity("threaded"))

        _threads = [threading.Thread(target=_worker) for _ in range(8)]
        for t in _threads:
            t.start()
        for t in _threads:
            t.join()

        assert _call_count["n"] == 1
        assert all(r is _results[0] for r in _results)
