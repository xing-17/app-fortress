"""
综合测试：app.common.core.loggroup

覆盖范围
--------
- TestResolvePath   _resolve_path() None 回退、字符串/Path 对象解析、~ 展开
- TestNew           new() 返回 FileGroup 实例，多次调用返回独立实例
- TestSingleton     GlobalLogGroupFactory / GlobalLogGroup 全局单例完整性
"""

from __future__ import annotations

from pathlib import Path

from xlog import FileGroup

from app.common.core.loggroup import CoreLogGroupFactory, GlobalLogGroup, GlobalLogGroupFactory

# ──────────────────────────────────────────────────────────────────────────────
# TestResolvePath
# ──────────────────────────────────────────────────────────────────────────────


class TestResolvePath:
    def test_none_returns_default(self):
        default = Path("/tmp/default_logs")
        result = CoreLogGroupFactory._resolve_path(path=None, default=default)
        assert result == default

    def test_str_path_returns_path_object(self):
        result = CoreLogGroupFactory._resolve_path(path="/tmp/my_logs")
        assert isinstance(result, Path)

    def test_path_object_returns_path_object(self):
        result = CoreLogGroupFactory._resolve_path(path=Path("/tmp/my_logs"))
        assert isinstance(result, Path)

    def test_tilde_is_expanded(self):
        result = CoreLogGroupFactory._resolve_path(path="~/logs")
        assert "~" not in str(result)

    def test_none_default_returns_none(self):
        result = CoreLogGroupFactory._resolve_path(path=None, default=None)
        assert result is None


# ──────────────────────────────────────────────────────────────────────────────
# TestNew
# ──────────────────────────────────────────────────────────────────────────────


class TestNew:
    def test_new_returns_filegroup(self):
        group = CoreLogGroupFactory.new("test_group")
        assert isinstance(group, FileGroup)

    def test_new_different_names_return_independent_instances(self):
        g1 = CoreLogGroupFactory.new("svc_a")
        g2 = CoreLogGroupFactory.new("svc_b")
        assert g1 is not g2

    def test_new_same_name_returns_new_instance_each_call(self):
        g1 = CoreLogGroupFactory.new("repeated")
        g2 = CoreLogGroupFactory.new("repeated")
        assert g1 is not g2


# ──────────────────────────────────────────────────────────────────────────────
# TestSingleton
# ──────────────────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_global_factory_is_coreloggroupfactory(self):
        assert isinstance(GlobalLogGroupFactory, CoreLogGroupFactory)

    def test_global_log_group_is_filegroup(self):
        assert isinstance(GlobalLogGroup, FileGroup)
