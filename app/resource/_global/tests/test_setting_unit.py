from __future__ import annotations

import threading

import pytest

from app.resource._global.setting import GlobalSetting
from app.setting.system import SystemSetting


class TestGlobalSettingLoad:
    def test_load_with_explicit_path_populates_attributes(self, tmp_path):
        (tmp_path / "system.yaml").write_text("name: test_system\n", encoding="utf-8")
        GlobalSetting.load(setting_path=tmp_path)
        assert GlobalSetting.setting_path == tmp_path.resolve()
        assert GlobalSetting.system_setting_path == (tmp_path / "system.yaml").resolve()
        assert isinstance(GlobalSetting.system_setting, SystemSetting)
        assert GlobalSetting.system_setting.name == "test_system"

    def test_load_uses_custom_system_file_name(self, tmp_path):
        (tmp_path / "custom.yaml").write_text("name: custom_system\n", encoding="utf-8")
        GlobalSetting.system_file_name = "custom.yaml"
        GlobalSetting.load(setting_path=tmp_path)
        assert GlobalSetting.system_setting.name == "custom_system"

    def test_load_missing_setting_path_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError):
            GlobalSetting.load(setting_path=tmp_path / "missing")

    def test_load_missing_system_file_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError):
            GlobalSetting.load(setting_path=tmp_path)

    def test_load_invalid_yaml_raises_value_error(self, tmp_path):
        (tmp_path / "system.yaml").write_text("key: [unbalanced\n", encoding="utf-8")
        with pytest.raises(ValueError):
            GlobalSetting.load(setting_path=tmp_path)


class TestGlobalSettingGetSystem:
    def test_get_system_lazy_loads_using_default_path(self, tmp_path, monkeypatch):
        (tmp_path / "system.yaml").write_text("name: lazy_system\n", encoding="utf-8")
        monkeypatch.setattr(GlobalSetting, "_default_setting_path", tmp_path)
        result = GlobalSetting.get_system()
        assert isinstance(result, SystemSetting)
        assert result.name == "lazy_system"

    def test_get_system_does_not_reload_when_already_cached(self, tmp_path, monkeypatch):
        (tmp_path / "system.yaml").write_text("name: cached_system\n", encoding="utf-8")
        GlobalSetting.load(setting_path=tmp_path)

        def _fail_load(cls, setting_path=None):
            raise AssertionError("load should not be called again")

        monkeypatch.setattr(GlobalSetting, "load", classmethod(_fail_load))
        result = GlobalSetting.get_system()
        assert result.name == "cached_system"


class TestGlobalSettingGetSettingPath:
    def test_get_setting_path_lazy_loads_using_default_path(self, tmp_path, monkeypatch):
        (tmp_path / "system.yaml").write_text("name: lazy_system\n", encoding="utf-8")
        monkeypatch.setattr(GlobalSetting, "_default_setting_path", tmp_path)
        result = GlobalSetting.get_setting_path()
        assert result == tmp_path.resolve()

    def test_get_setting_path_does_not_reload_when_already_cached(self, tmp_path, monkeypatch):
        (tmp_path / "system.yaml").write_text("name: cached_system\n", encoding="utf-8")
        GlobalSetting.load(setting_path=tmp_path)

        def _fail_load(cls, setting_path=None):
            raise AssertionError("load should not be called again")

        monkeypatch.setattr(GlobalSetting, "load", classmethod(_fail_load))
        result = GlobalSetting.get_setting_path()
        assert result == tmp_path.resolve()


class TestGlobalSettingReset:
    def test_reset_restores_all_defaults(self, tmp_path):
        (tmp_path / "system.yaml").write_text("name: to_be_reset\n", encoding="utf-8")
        GlobalSetting.load(setting_path=tmp_path)
        GlobalSetting.system_file_name = "changed.yaml"

        GlobalSetting.reset()

        assert GlobalSetting.setting_path is None
        assert GlobalSetting.system_setting_path is None
        assert GlobalSetting.system_setting is None
        assert GlobalSetting.system_file_name == "system.yaml"


class TestGlobalSettingConcurrency:
    def test_get_system_under_concurrent_access_loads_only_once(self, tmp_path, monkeypatch):
        (tmp_path / "system.yaml").write_text("name: threaded_system\n", encoding="utf-8")
        monkeypatch.setattr(GlobalSetting, "_default_setting_path", tmp_path)

        _original_from_yaml = SystemSetting.from_yaml
        _call_count = {"n": 0}

        def _counting_from_yaml(cls, path):
            _call_count["n"] += 1
            return _original_from_yaml(path)

        monkeypatch.setattr(SystemSetting, "from_yaml", classmethod(_counting_from_yaml))

        _results: list[SystemSetting] = []
        _barrier = threading.Barrier(8)

        def _worker():
            _barrier.wait()
            _results.append(GlobalSetting.get_system())

        _threads = [threading.Thread(target=_worker) for _ in range(8)]
        for t in _threads:
            t.start()
        for t in _threads:
            t.join()

        assert _call_count["n"] == 1
        assert all(r is _results[0] for r in _results)
