"""
综合测试：app.common.core.logstream

覆盖范围
--------
- TestResolveLogFormat  _resolve_log_format() 已知格式映射、未知格式 Text 回退、大小写容忍
- TestNew               new() 返回 LogStream 实例，多次调用返回独立实例
- TestSingleton         GlobalLogStreamFactory / GlobalLogStream 全局单例完整性
"""

from __future__ import annotations

import pytest
from xlog import ColorText, ColorTree, FormatLike, LogStream, Text, Tree

from app.common.core.logstream import CoreLogStreamFactory, GlobalLogStream, GlobalLogStreamFactory
from app.common.core.setting import GlobalSetting

_FORMAT_CASES = [
    ("TEXT", Text),
    ("TREE", Tree),
    ("COLORTEXT", ColorText),
    ("COLORTREE", ColorTree),
]


# ──────────────────────────────────────────────────────────────────────────────
# TestResolveLogFormat
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveLogFormat:
    @pytest.mark.parametrize("fmt_name, expected_type", _FORMAT_CASES)
    def test_known_format_returns_correct_type(self, fmt_name, expected_type, monkeypatch):
        monkeypatch.setattr(GlobalSetting.system, "log_format", fmt_name)
        result = CoreLogStreamFactory._resolve_log_format()
        assert isinstance(result, expected_type)

    def test_unknown_format_falls_back_to_text(self, monkeypatch):
        monkeypatch.setattr(GlobalSetting.system, "log_format", "UNKNOWN")
        result = CoreLogStreamFactory._resolve_log_format()
        assert isinstance(result, Text)

    def test_lowercase_format_name_normalized(self, monkeypatch):
        monkeypatch.setattr(GlobalSetting.system, "log_format", "text")
        result = CoreLogStreamFactory._resolve_log_format()
        assert isinstance(result, Text)

    def test_result_is_format_like(self, monkeypatch):
        monkeypatch.setattr(GlobalSetting.system, "log_format", "TEXT")
        result = CoreLogStreamFactory._resolve_log_format()
        assert isinstance(result, FormatLike)


# ──────────────────────────────────────────────────────────────────────────────
# TestNew
# ──────────────────────────────────────────────────────────────────────────────


class TestNew:
    def test_new_returns_logstream(self):
        stream = CoreLogStreamFactory.new("test_stream")
        assert isinstance(stream, LogStream)

    def test_new_different_names_return_independent_instances(self):
        s1 = CoreLogStreamFactory.new("svc_a")
        s2 = CoreLogStreamFactory.new("svc_b")
        assert s1 is not s2

    def test_new_same_name_returns_new_instance_each_call(self):
        s1 = CoreLogStreamFactory.new("repeated")
        s2 = CoreLogStreamFactory.new("repeated")
        assert s1 is not s2


# ──────────────────────────────────────────────────────────────────────────────
# TestSingleton
# ──────────────────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_global_factory_is_corelogstreamfactory(self):
        assert isinstance(GlobalLogStreamFactory, CoreLogStreamFactory)

    def test_global_log_stream_is_logstream(self):
        assert isinstance(GlobalLogStream, LogStream)
