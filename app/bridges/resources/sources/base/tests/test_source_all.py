"""
综合测试：app.bridges.resources.sources.base.source

覆盖范围
--------
- TestInit          __init__ 正确从 setting 初始化字段
- TestAbstract      未实现 build_params 时无法实例化
- TestBuildParams   子类实现 build_params 方法的正确行为
- TestExport        export() 返回正确的字典结构
- TestPlugins       验证继承的 Plugin 行为
"""

from __future__ import annotations

import pytest

from app.bridges.resources.sources.base.setting import (
    BaseSourceSetting,
    PartitionSetting,
)
from app.bridges.resources.sources.base.source import BaseSource

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


_MOCK_SETTING = BaseSourceSetting(
    name="test_source",
    provider_type="tushare",
    method="daily",
    strategy="by_date",
    partition=PartitionSetting(prefix="date", column="trade_date"),
)


class _MockSource(BaseSource):
    """测试用具体实现"""

    def build_params(self, **kwargs) -> dict:
        return {"method": self.setting.method, **kwargs}


class _NoParamsSource(BaseSource):
    """缺少 build_params 实现的类"""

    pass


# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    def test_setting_is_stored(self):
        s = _MockSource(setting=_MOCK_SETTING)
        assert s.setting is _MOCK_SETTING

    def test_name_set_from_setting(self):
        s = _MockSource(setting=_MOCK_SETTING)
        assert s.name == "test_source"

    def test_name_matches_setting_name(self):
        custom_setting = BaseSourceSetting(
            name="custom_name",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
        )
        s = _MockSource(setting=custom_setting)
        assert s.name == custom_setting.name

    def test_different_instances_have_independent_settings(self):
        setting1 = BaseSourceSetting(
            name="source1",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
        )
        setting2 = BaseSourceSetting(
            name="source2",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
        )
        s1 = _MockSource(setting=setting1)
        s2 = _MockSource(setting=setting2)
        assert s1.name != s2.name
        assert s1.setting is not s2.setting


# ──────────────────────────────────────────────────────────────────────────────
# TestAbstract
# ──────────────────────────────────────────────────────────────────────────────


class TestAbstract:
    def test_build_params_not_implemented_raises(self):
        """验证未实现 build_params 会抛出 NotImplementedError"""

        class _NoImpl(BaseSource):
            pass

        s = _NoImpl(setting=_MOCK_SETTING)
        with pytest.raises(NotImplementedError):
            s.build_params()


# ──────────────────────────────────────────────────────────────────────────────
# TestBuildParams
# ──────────────────────────────────────────────────────────────────────────────


class TestBuildParams:
    def test_build_params_returns_dict(self):
        s = _MockSource(setting=_MOCK_SETTING)
        result = s.build_params()
        assert isinstance(result, dict)

    def test_build_params_receives_kwargs(self):
        s = _MockSource(setting=_MOCK_SETTING)
        result = s.build_params(date="20240101", symbol="000001")
        assert result["date"] == "20240101"
        assert result["symbol"] == "000001"

    def test_build_params_can_access_setting(self):
        s = _MockSource(setting=_MOCK_SETTING)
        result = s.build_params()
        assert result["method"] == "daily"

    def test_build_params_empty_kwargs(self):
        s = _MockSource(setting=_MOCK_SETTING)
        result = s.build_params()
        assert "method" in result
        assert result["method"] == _MOCK_SETTING.method


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        s = _MockSource(setting=_MOCK_SETTING)
        result = s.export()
        assert isinstance(result, dict)

    def test_export_includes_name(self):
        s = _MockSource(setting=_MOCK_SETTING)
        result = s.export()
        assert "name" in result
        assert result["name"] == "test_source"

    def test_export_includes_setting(self):
        s = _MockSource(setting=_MOCK_SETTING)
        result = s.export()
        assert "setting" in result
        assert isinstance(result["setting"], dict)

    def test_export_setting_is_setting_export(self):
        s = _MockSource(setting=_MOCK_SETTING)
        result = s.export()
        expected_setting = _MOCK_SETTING.export()
        assert result["setting"] == expected_setting

    def test_export_name_matches_setting_name(self):
        s = _MockSource(setting=_MOCK_SETTING)
        result = s.export()
        assert result["name"] == _MOCK_SETTING.name


# ──────────────────────────────────────────────────────────────────────────────
# TestPlugins
# ──────────────────────────────────────────────────────────────────────────────


class TestPlugins:
    def test_inherits_logplugin(self):
        """验证继承了 LogPlugin"""
        from app.common.plugin import LogPlugin

        s = _MockSource(setting=_MOCK_SETTING)
        assert isinstance(s, LogPlugin)

    def test_inherits_timeplugin(self):
        """验证继承了 TimePlugin"""
        from app.common.plugin import TimePlugin

        s = _MockSource(setting=_MOCK_SETTING)
        assert isinstance(s, TimePlugin)

    def test_inherits_stopwatchplugin(self):
        """验证继承了 StopwatchPlugin"""
        from app.common.plugin import StopwatchPlugin

        s = _MockSource(setting=_MOCK_SETTING)
        assert isinstance(s, StopwatchPlugin)

    def test_has_log_method(self):
        """验证有 log 方法（来自 LogPlugin）"""
        s = _MockSource(setting=_MOCK_SETTING)
        assert hasattr(s, "log")
        assert callable(s.log)

    def test_has_info_method(self):
        """验证有 info 方法"""
        s = _MockSource(setting=_MOCK_SETTING)
        assert hasattr(s, "info")
        assert callable(s.info)

    def test_has_debug_method(self):
        """验证有 debug 方法"""
        s = _MockSource(setting=_MOCK_SETTING)
        assert hasattr(s, "debug")
        assert callable(s.debug)
