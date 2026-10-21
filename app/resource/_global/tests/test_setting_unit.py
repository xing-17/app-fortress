from __future__ import annotations

import threading

import pytest

from app.internal.constant.servicekind import ServiceKind
from app.resource._global.setting import GlobalSetting
from app.setting.service import ServicesSetting
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


class TestGlobalSettingLoadServices:
    def test_load_without_services_file_uses_defaults(self, tmp_path):
        (tmp_path / "system.yaml").write_text("name: test_system\n", encoding="utf-8")
        GlobalSetting.load(setting_path=tmp_path)
        assert GlobalSetting.services_setting_path is None
        assert isinstance(GlobalSetting.services_setting, ServicesSetting)
        assert GlobalSetting.services_setting == ServicesSetting()

    def test_load_with_services_file_populates_attributes(self, tmp_path):
        (tmp_path / "system.yaml").write_text("name: test_system\n", encoding="utf-8")
        (tmp_path / "services.yaml").write_text(
            "node:\n  port: 9100\nwebhost:\n  enabled: false\n",
            encoding="utf-8",
        )
        GlobalSetting.load(setting_path=tmp_path)
        assert GlobalSetting.services_setting_path == (tmp_path / "services.yaml").resolve()
        assert isinstance(GlobalSetting.services_setting, ServicesSetting)
        assert GlobalSetting.services_setting.node.port == 9100
        assert GlobalSetting.services_setting.webhost.enabled is False

    def test_load_services_file_omitted_blocks_use_defaults(self, tmp_path):
        (tmp_path / "system.yaml").write_text("name: test_system\n", encoding="utf-8")
        (tmp_path / "services.yaml").write_text("node:\n  port: 9100\n", encoding="utf-8")
        GlobalSetting.load(setting_path=tmp_path)
        _services = GlobalSetting.services_setting
        assert _services.machine.kind == ServiceKind.MACHINE
        assert _services.mcphost.port == 8801
        assert _services.webhost.port == 8802

    def test_load_uses_custom_services_file_name(self, tmp_path):
        (tmp_path / "system.yaml").write_text("name: test_system\n", encoding="utf-8")
        (tmp_path / "custom_services.yaml").write_text("node:\n  port: 9200\n", encoding="utf-8")
        (tmp_path / "services.yaml").write_text("node:\n  port: 9100\n", encoding="utf-8")
        GlobalSetting.services_file_name = "custom_services.yaml"
        GlobalSetting.load(setting_path=tmp_path)
        assert GlobalSetting.services_setting.node.port == 9200

    def test_load_invalid_services_yaml_raises_value_error(self, tmp_path):
        (tmp_path / "system.yaml").write_text("name: test_system\n", encoding="utf-8")
        (tmp_path / "services.yaml").write_text("key: [unbalanced\n", encoding="utf-8")
        with pytest.raises(ValueError):
            GlobalSetting.load(setting_path=tmp_path)

    def test_load_invalid_services_value_raises(self, tmp_path):
        (tmp_path / "system.yaml").write_text("name: test_system\n", encoding="utf-8")
        (tmp_path / "services.yaml").write_text("node:\n  port: 70000\n", encoding="utf-8")
        with pytest.raises(ValueError):
            GlobalSetting.load(setting_path=tmp_path)

    def test_load_services_failure_keeps_previous_state(self, tmp_path):
        _good = tmp_path / "good"
        _bad = tmp_path / "bad"
        _good.mkdir()
        _bad.mkdir()
        (_good / "system.yaml").write_text("name: good_system\n", encoding="utf-8")
        (_bad / "system.yaml").write_text("name: bad_system\n", encoding="utf-8")
        (_bad / "services.yaml").write_text("key: [unbalanced\n", encoding="utf-8")
        GlobalSetting.load(setting_path=_good)
        with pytest.raises(ValueError):
            GlobalSetting.load(setting_path=_bad)
        assert GlobalSetting.setting_path == _good.resolve()
        assert GlobalSetting.system_setting.name == "good_system"

    def test_load_reload_without_services_file_clears_previous_path(self, tmp_path):
        _first = tmp_path / "first"
        _second = tmp_path / "second"
        _first.mkdir()
        _second.mkdir()
        (_first / "system.yaml").write_text("name: first\n", encoding="utf-8")
        (_first / "services.yaml").write_text("node:\n  port: 9100\n", encoding="utf-8")
        (_second / "system.yaml").write_text("name: second\n", encoding="utf-8")
        GlobalSetting.load(setting_path=_first)
        GlobalSetting.load(setting_path=_second)
        assert GlobalSetting.services_setting_path is None
        assert GlobalSetting.services_setting.node.port == 8800

    def test_load_repo_settings_directory(self):
        # The shipped settings/ directory must always load cleanly.
        GlobalSetting.load()
        assert isinstance(GlobalSetting.services_setting, ServicesSetting)
        assert GlobalSetting.services_setting_path is not None


class TestGlobalSettingGetServices:
    def test_get_services_lazy_loads_using_default_path(self, tmp_path, monkeypatch):
        (tmp_path / "system.yaml").write_text("name: lazy_system\n", encoding="utf-8")
        (tmp_path / "services.yaml").write_text("node:\n  port: 9300\n", encoding="utf-8")
        monkeypatch.setattr(GlobalSetting, "_default_setting_path", tmp_path)
        result = GlobalSetting.get_services()
        assert isinstance(result, ServicesSetting)
        assert result.node.port == 9300

    def test_get_services_without_file_returns_defaults(self, tmp_path, monkeypatch):
        (tmp_path / "system.yaml").write_text("name: lazy_system\n", encoding="utf-8")
        monkeypatch.setattr(GlobalSetting, "_default_setting_path", tmp_path)
        assert GlobalSetting.get_services() == ServicesSetting()

    def test_get_services_does_not_reload_when_already_cached(self, tmp_path, monkeypatch):
        (tmp_path / "system.yaml").write_text("name: cached_system\n", encoding="utf-8")
        (tmp_path / "services.yaml").write_text("node:\n  port: 9400\n", encoding="utf-8")
        GlobalSetting.load(setting_path=tmp_path)

        def _fail_load(cls, setting_path=None):
            raise AssertionError("load should not be called again")

        monkeypatch.setattr(GlobalSetting, "load", classmethod(_fail_load))
        assert GlobalSetting.get_services().node.port == 9400

    def test_get_services_returns_same_instance(self, tmp_path):
        (tmp_path / "system.yaml").write_text("name: cached_system\n", encoding="utf-8")
        GlobalSetting.load(setting_path=tmp_path)
        assert GlobalSetting.get_services() is GlobalSetting.get_services()


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
        (tmp_path / "services.yaml").write_text("node:\n  port: 9100\n", encoding="utf-8")
        GlobalSetting.load(setting_path=tmp_path)
        GlobalSetting.system_file_name = "changed.yaml"
        GlobalSetting.services_file_name = "changed_services.yaml"

        GlobalSetting.reset()

        assert GlobalSetting.setting_path is None
        assert GlobalSetting.system_setting_path is None
        assert GlobalSetting.system_setting is None
        assert GlobalSetting.system_file_name == "system.yaml"
        assert GlobalSetting.services_setting_path is None
        assert GlobalSetting.services_setting is None
        assert GlobalSetting.services_file_name == "services.yaml"


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

    def test_get_services_under_concurrent_access_returns_same_instance(self, tmp_path, monkeypatch):
        (tmp_path / "system.yaml").write_text("name: threaded_system\n", encoding="utf-8")
        (tmp_path / "services.yaml").write_text("node:\n  port: 9500\n", encoding="utf-8")
        monkeypatch.setattr(GlobalSetting, "_default_setting_path", tmp_path)

        _results: list[ServicesSetting] = []
        _barrier = threading.Barrier(8)

        def _worker():
            _barrier.wait()
            _results.append(GlobalSetting.get_services())

        _threads = [threading.Thread(target=_worker) for _ in range(8)]
        for t in _threads:
            t.start()
        for t in _threads:
            t.join()

        assert len(_results) == 8
        assert all(r is _results[0] for r in _results)
        assert _results[0].node.port == 9500
