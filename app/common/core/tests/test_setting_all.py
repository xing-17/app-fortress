"""
综合测试：app.common.core.setting

覆盖范围
--------
- TestLoad      默认/自定义路径加载；缺失文件、空/非法 YAML 时抛出正确异常；connections/cache 路径与字段正确记录
- TestRefresh   refresh() 不抛异常；刷新后字段值与文件一致；connections/cache 持久正确
- TestDescribe  describe() 返回包含 system/connections/cache 的正确结构
- TestSingleton GlobalSetting 全局单例完整性，connections 和 cache 可访问
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.common.core.setting import CoreSetting, GlobalSetting
from app.common.setting.cache import CacheSetting
from app.common.setting.connections import ConnectionsSetting, OssConnectionSetting

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

VALID_CONNECTIONS_YAML = {
    "connections": {
        "prod": {
            "type": "oss",
            "access_key_id": "LTAI5tTEST",
            "access_key_secret": "SECRET5678",
            "endpoint": "oss-cn-shanghai.aliyuncs.com",
            "region": "cn-shanghai",
            "bucket": "test-bucket",
        }
    }
}

VALID_CACHE_YAML = {
    "url": "sqlite:///tmp/test_cache.db",
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


@pytest.fixture
def valid_conns_yaml_path(tmp_path: Path) -> Path:
    path = tmp_path / "connections.yml"
    path.write_text(yaml.dump(VALID_CONNECTIONS_YAML, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def valid_cache_yaml_path(tmp_path: Path) -> Path:
    path = tmp_path / "cache.yml"
    path.write_text(yaml.dump(VALID_CACHE_YAML, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def restore_class_paths():
    """Restore all CoreSetting class-level paths after each test."""
    orig_sys = CoreSetting._system_path
    orig_conns = CoreSetting._conns_path
    orig_cache = CoreSetting._cache_path
    yield
    CoreSetting._system_path = orig_sys
    CoreSetting._conns_path = orig_conns
    CoreSetting._cache_path = orig_cache


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

    def test_load_populates_connections(self):
        setting = CoreSetting.load()
        assert isinstance(setting.connections, ConnectionsSetting)

    def test_load_populates_cache(self):
        setting = CoreSetting.load()
        assert isinstance(setting.cache, CacheSetting)

    def test_load_custom_conns_path(self, valid_conns_yaml_path):
        setting = CoreSetting.load(conns_path=valid_conns_yaml_path)
        assert isinstance(setting.connections, ConnectionsSetting)

    def test_load_custom_cache_path(self, valid_cache_yaml_path):
        setting = CoreSetting.load(cache_path=valid_cache_yaml_path)
        assert isinstance(setting.cache, CacheSetting)

    def test_load_stores_conns_path(self, valid_conns_yaml_path):
        CoreSetting.load(conns_path=valid_conns_yaml_path)
        assert CoreSetting._conns_path == valid_conns_yaml_path

    def test_load_stores_cache_path(self, valid_cache_yaml_path):
        CoreSetting.load(cache_path=valid_cache_yaml_path)
        assert CoreSetting._cache_path == valid_cache_yaml_path

    def test_load_missing_conns_raises_filenotfounderror(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            CoreSetting.load(conns_path=tmp_path / "nonexistent_conns.yml")

    def test_load_missing_cache_raises_filenotfounderror(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            CoreSetting.load(cache_path=tmp_path / "nonexistent_cache.yml")


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

    def test_refresh_retains_connections(self):
        GlobalSetting.refresh()
        assert isinstance(GlobalSetting.connections, ConnectionsSetting)

    def test_refresh_retains_cache(self):
        GlobalSetting.refresh()
        assert isinstance(GlobalSetting.cache, CacheSetting)


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_describe_returns_str(self):
        assert isinstance(GlobalSetting.describe(), str)

    def test_describe_contains_system_key(self):
        assert "system" in GlobalSetting.describe()

    def test_describe_contains_connections_key(self):
        assert "connections" in GlobalSetting.describe()

    def test_describe_contains_cache_key(self):
        assert "cache" in GlobalSetting.describe()


# ──────────────────────────────────────────────────────────────────────────────
# TestSingleton
# ──────────────────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_global_setting_is_coresetting(self):
        assert isinstance(GlobalSetting, CoreSetting)

    def test_global_setting_system_name_is_fortress(self):
        assert GlobalSetting.system.name == "fortress"

    def test_global_setting_has_connections_setting(self):
        assert isinstance(GlobalSetting.connections, ConnectionsSetting)

    def test_global_setting_has_cache_setting(self):
        assert isinstance(GlobalSetting.cache, CacheSetting)

    def test_global_setting_connections_get_prod(self):
        conn = GlobalSetting.connections.get("prod")
        assert isinstance(conn, OssConnectionSetting)
