"""
综合测试：app.common.core.setting

覆盖范围
--------
- TestLoad      默认/自定义路径加载；缺失文件、空 YAML、非法 YAML 时抛出正确异常；加载后 _system_path 正确记录
- TestRefresh   refresh() 不抛异常；刷新后字段值与文件一致；文件更新后值随之更新
- TestDescribe  describe() 返回正确结构
- TestSingleton GlobalSetting 全局单例完整性
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.common.core.setting import CoreSetting, GlobalSetting

VALID_YAML = {
    "name": "test-fortress",
    "version": "1.0.0",
    "alias": "test",
    "env": "test",
    "timezone": "UTC",
    "log_level": "INFO",
    "log_format": "TEXT",
    "log_path": "./test_logs",
    "log_file_max_mb": 5,
    "log_group_max_len": 100,
}


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def valid_yaml_path(tmp_path: Path) -> Path:
    path = tmp_path / "system.yml"
    path.write_text(yaml.dump(VALID_YAML, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def empty_yaml_path(tmp_path: Path) -> Path:
    path = tmp_path / "empty.yml"
    path.write_text("", encoding="utf-8")
    return path


@pytest.fixture
def invalid_yaml_path(tmp_path: Path) -> Path:
    path = tmp_path / "invalid.yml"
    path.write_text("name: [unclosed", encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def restore_system_path():
    """Restore CoreSetting._system_path after each test to avoid cross-test side effects."""
    original = CoreSetting._system_path
    yield
    CoreSetting._system_path = original


# ──────────────────────────────────────────────────────────────────────────────
# TestLoad
# ──────────────────────────────────────────────────────────────────────────────


class TestLoad:
    def test_load_default_path_returns_coresetting(self):
        setting = CoreSetting.load()
        assert isinstance(setting, CoreSetting)

    def test_load_custom_path_returns_coresetting(self, valid_yaml_path):
        setting = CoreSetting.load(system_path=valid_yaml_path)
        assert isinstance(setting, CoreSetting)

    def test_load_stores_system_path(self, valid_yaml_path):
        CoreSetting.load(system_path=valid_yaml_path)
        assert CoreSetting._system_path == valid_yaml_path

    def test_load_populates_system_name(self, valid_yaml_path):
        setting = CoreSetting.load(system_path=valid_yaml_path)
        assert setting.system.name == VALID_YAML["name"]

    def test_load_missing_file_raises_filenotfounderror(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            CoreSetting.load(system_path=tmp_path / "nonexistent.yml")

    def test_load_empty_yaml_raises_valueerror(self, empty_yaml_path):
        with pytest.raises(ValueError):
            CoreSetting.load(system_path=empty_yaml_path)

    def test_load_invalid_yaml_raises_valueerror(self, invalid_yaml_path):
        with pytest.raises(ValueError):
            CoreSetting.load(system_path=invalid_yaml_path)


# ──────────────────────────────────────────────────────────────────────────────
# TestRefresh
# ──────────────────────────────────────────────────────────────────────────────


class TestRefresh:
    def test_refresh_does_not_raise(self):
        GlobalSetting.refresh()

    def test_refresh_retains_correct_name(self):
        GlobalSetting.refresh()
        assert GlobalSetting.system.name == "fortress"

    def test_refresh_picks_up_file_changes(self, valid_yaml_path):
        setting = CoreSetting.load(system_path=valid_yaml_path)
        assert setting.system.name == "test-fortress"

        updated = {**VALID_YAML, "name": "updated-fortress"}
        valid_yaml_path.write_text(yaml.dump(updated, allow_unicode=True), encoding="utf-8")

        setting.refresh()
        assert setting.system.name == "updated-fortress"


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_describe_returns_dict(self):
        assert isinstance(GlobalSetting.describe(), dict)

    def test_describe_contains_system_key(self):
        assert "system" in GlobalSetting.describe()

    def test_describe_system_value_is_dict(self):
        assert isinstance(GlobalSetting.describe()["system"], dict)


# ──────────────────────────────────────────────────────────────────────────────
# TestSingleton
# ──────────────────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_global_setting_is_coresetting(self):
        assert isinstance(GlobalSetting, CoreSetting)

    def test_global_setting_system_name_is_fortress(self):
        assert GlobalSetting.system.name == "fortress"
