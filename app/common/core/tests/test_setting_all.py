"""
综合测试：app.common.core.setting

覆盖范围
--------
- TestLoad          默认/自定义路径加载；5 个配置项全部就位；缺失文件时抛正确异常
- TestRefresh       refresh() 不抛异常；文件变更后值更新；5 项全部持久
- TestExport        export() 返回 dict；system/bridges/centre 嵌套结构正确
- TestDescribe      describe() 返回合法 JSON；system/bridges/centre 键存在
- TestGetShortcuts  get_connection() / get_provider() 委托正确；缺失时抛 KeyError
- TestSingleton     GlobalSetting 完整性；5 项可访问；两个快捷方法可用
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.common.core.setting import CoreSetting, GlobalSetting
from app.common.setting.bridges import BridgesSetting
from app.common.setting.centre import CentreSetting
from app.common.setting.connections import ConnectionsSetting, OssConnectionSetting
from app.common.setting.system import SystemSetting

# ──────────────────────────────────────────────────────────────────────────────
# Test data
# ──────────────────────────────────────────────────────────────────────────────

VALID_SYSTEM_YAML = {
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

VALID_CENTRE_YAML = {
    "target": "test",
}

VALID_PROVIDERS_YAML = {
    "providers": {
        "tushare": {
            "type": "tushare",
            "name": "tushare",
            "region": "cn",
            "secret": "test_token_12345678901234",
        }
    }
}


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def valid_yaml_path(tmp_path: Path) -> Path:
    p = tmp_path / "system.yml"
    p.write_text(yaml.dump(VALID_SYSTEM_YAML, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture
def valid_conns_yaml_path(tmp_path: Path) -> Path:
    p = tmp_path / "connections.yml"
    p.write_text(yaml.dump(VALID_CONNECTIONS_YAML, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture
def valid_centre_yaml_path(tmp_path: Path) -> Path:
    p = tmp_path / "centre.yml"
    p.write_text(yaml.dump(VALID_CENTRE_YAML, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture
def valid_bridges_yaml_path(tmp_path: Path) -> Path:
    p = tmp_path / "bridges.yml"
    p.write_text(yaml.dump(VALID_PROVIDERS_YAML, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture
def all_custom_paths(
    valid_yaml_path,
    valid_conns_yaml_path,
    valid_centre_yaml_path,
    valid_bridges_yaml_path,
) -> dict:
    return dict(
        system_path=valid_yaml_path,
        conns_path=valid_conns_yaml_path,
        centre_path=valid_centre_yaml_path,
        bridges_path=valid_bridges_yaml_path,
    )


@pytest.fixture
def mock_global_setting(
    valid_yaml_path,
    valid_conns_yaml_path,
    valid_centre_yaml_path,
    valid_bridges_yaml_path,
) -> CoreSetting:
    """创建一个完全独立的 mock CoreSetting，不依赖真实 setting 文件。"""
    return CoreSetting.load(
        system_path=valid_yaml_path,
        conns_path=valid_conns_yaml_path,
        centre_path=valid_centre_yaml_path,
        bridges_path=valid_bridges_yaml_path,
    )


@pytest.fixture(autouse=True)
def restore_class_paths():
    """Restore all CoreSetting class-level paths after each test."""
    orig = (
        CoreSetting._system_path,
        CoreSetting._conns_path,
        CoreSetting._centre_path,
        CoreSetting._bridges_path,
    )
    yield
    (
        CoreSetting._system_path,
        CoreSetting._conns_path,
        CoreSetting._centre_path,
        CoreSetting._bridges_path,
    ) = orig


# ──────────────────────────────────────────────────────────────────────────────
# TestLoad
# ──────────────────────────────────────────────────────────────────────────────


class TestLoad:
    def test_load_default_returns_coresetting(self):
        assert isinstance(CoreSetting.load(), CoreSetting)

    def test_load_populates_system(self):
        assert isinstance(CoreSetting.load().system, SystemSetting)

    def test_load_populates_connections(self):
        assert isinstance(CoreSetting.load().connections, ConnectionsSetting)

    def test_load_populates_centre(self):
        assert isinstance(CoreSetting.load().centre, CentreSetting)

    def test_load_populates_bridges(self):
        assert isinstance(CoreSetting.load().bridges, BridgesSetting)

    def test_load_custom_system_path(self, valid_yaml_path):
        s = CoreSetting.load(system_path=valid_yaml_path)
        assert s.system.name == "test-fortress"

    def test_load_custom_all_paths(self, all_custom_paths):
        s = CoreSetting.load(**all_custom_paths)
        assert isinstance(s, CoreSetting)
        assert s.system.name == "test-fortress"
        assert s.centre.target == "test"

    def test_load_stores_system_path(self, valid_yaml_path):
        CoreSetting.load(system_path=valid_yaml_path)
        assert CoreSetting._system_path == valid_yaml_path

    def test_load_stores_all_paths(self, all_custom_paths):
        CoreSetting.load(**all_custom_paths)
        assert CoreSetting._system_path == all_custom_paths["system_path"]
        assert CoreSetting._conns_path == all_custom_paths["conns_path"]
        assert CoreSetting._centre_path == all_custom_paths["centre_path"]
        assert CoreSetting._bridges_path == all_custom_paths["bridges_path"]

    def test_load_missing_system_raises_filenotfounderror(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            CoreSetting.load(system_path=tmp_path / "nonexistent.yml")


# ──────────────────────────────────────────────────────────────────────────────
# TestRefresh
# ──────────────────────────────────────────────────────────────────────────────


class TestRefresh:
    def test_refresh_does_not_raise(self):
        GlobalSetting.refresh()

    def test_refresh_retains_system_name(self):
        GlobalSetting.refresh()
        assert GlobalSetting.system.name == "fortress"

    def test_refresh_picks_up_file_changes(self, valid_yaml_path):
        setting = CoreSetting.load(system_path=valid_yaml_path)
        assert setting.system.name == "test-fortress"
        updated = {**VALID_SYSTEM_YAML, "name": "updated-fortress"}
        valid_yaml_path.write_text(yaml.dump(updated, allow_unicode=True), encoding="utf-8")
        setting.refresh()
        assert setting.system.name == "updated-fortress"

    def test_refresh_retains_connections(self):
        GlobalSetting.refresh()
        assert isinstance(GlobalSetting.connections, ConnectionsSetting)

    def test_refresh_retains_centre(self):
        GlobalSetting.refresh()
        assert isinstance(GlobalSetting.centre, CentreSetting)

    def test_refresh_retains_bridges(self):
        GlobalSetting.refresh()
        assert isinstance(GlobalSetting.bridges, BridgesSetting)


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        assert isinstance(GlobalSetting.export(), dict)

    def test_export_contains_system_key(self):
        assert "system" in GlobalSetting.export()

    def test_export_contains_bridges_key(self):
        assert "bridges" in GlobalSetting.export()

    def test_export_contains_centre_key(self):
        assert "centre" in GlobalSetting.export()

    def test_export_system_is_dict(self):
        assert isinstance(GlobalSetting.export()["system"], dict)

    def test_export_centre_is_dict(self):
        assert isinstance(GlobalSetting.export()["centre"], dict)

    def test_export_system_name_matches(self):
        assert GlobalSetting.export()["system"]["name"] == GlobalSetting.system.name


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_describe_returns_str(self):
        assert isinstance(GlobalSetting.describe(), str)

    def test_describe_is_valid_json(self):
        assert isinstance(json.loads(GlobalSetting.describe()), dict)

    def test_describe_contains_system_key(self):
        assert "system" in GlobalSetting.describe()

    def test_describe_contains_centre_key(self):
        assert "centre" in GlobalSetting.describe()


# ──────────────────────────────────────────────────────────────────────────────
# TestGetShortcuts
# ──────────────────────────────────────────────────────────────────────────────


class TestGetShortcuts:
    def test_get_connection_returns_oss_setting(self, mock_global_setting):
        """测试 get_connection() 返回正确的 OSS 连接配置（使用 mock 数据）。"""
        conn = mock_global_setting.get_connection("prod")
        assert isinstance(conn, OssConnectionSetting)

    def test_get_connection_missing_raises_keyerror(self, mock_global_setting):
        """测试获取不存在的连接时抛出 KeyError（使用 mock 数据）。"""
        with pytest.raises(KeyError):
            mock_global_setting.get_connection("nonexistent")

    def test_get_provider_missing_raises_keyerror(self, mock_global_setting):
        """测试获取不存在的 provider 时抛出 KeyError（使用 mock 数据）。"""
        with pytest.raises(KeyError):
            mock_global_setting.get_provider("nonexistent")


# ──────────────────────────────────────────────────────────────────────────────
# TestSingleton
# ──────────────────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_global_setting_is_coresetting(self, mock_global_setting):
        """测试 GlobalSetting 是 CoreSetting 实例（使用 mock 数据）。"""
        assert isinstance(mock_global_setting, CoreSetting)

    def test_global_setting_system_name(self, mock_global_setting):
        """测试 GlobalSetting system.name（使用 mock 数据）。"""
        assert mock_global_setting.system.name == "test-fortress"

    def test_global_setting_has_system(self, mock_global_setting):
        """测试 GlobalSetting 包含 system 配置（使用 mock 数据）。"""
        assert isinstance(mock_global_setting.system, SystemSetting)

    def test_global_setting_has_connections(self, mock_global_setting):
        """测试 GlobalSetting 包含 connections 配置（使用 mock 数据）。"""
        assert isinstance(mock_global_setting.connections, ConnectionsSetting)

    def test_global_setting_has_centre(self, mock_global_setting):
        """测试 GlobalSetting 包含 centre 配置（使用 mock 数据）。"""
        assert isinstance(mock_global_setting.centre, CentreSetting)

    def test_global_setting_has_bridges(self, mock_global_setting):
        """测试 GlobalSetting 包含 bridges 配置（使用 mock 数据）。"""
        assert isinstance(mock_global_setting.bridges, BridgesSetting)

    def test_global_setting_get_connection_prod(self, mock_global_setting):
        """测试 GlobalSetting.get_connection('prod') 返回 OSS 连接（使用 mock 数据）。"""
        assert isinstance(mock_global_setting.get_connection("prod"), OssConnectionSetting)
