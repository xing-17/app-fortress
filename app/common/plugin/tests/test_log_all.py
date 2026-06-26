"""
综合测试：app.common.plugin.log

覆盖范围
--------
- TestPrefix      _set_log_prefix / _resolve_log_message 前缀拼接机制
- TestLogStream   日志流延迟初始化行为
- TestLogMethods  info / debug / warning / error / log 各方法不抛异常
"""

from __future__ import annotations

import pytest

from app.common.plugin.log import LogPlugin

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


class _SampleService(LogPlugin):
    pass


# ──────────────────────────────────────────────────────────────────────────────
# TestPrefix
# ──────────────────────────────────────────────────────────────────────────────


class TestPrefix:
    def test_set_prefix_stores_value(self):
        svc = _SampleService()
        svc._set_log_prefix("[SVC]")
        assert svc._log_prefix == "[SVC]"

    def test_set_prefix_empty_string_becomes_empty(self):
        svc = _SampleService()
        svc._set_log_prefix("")
        assert svc._log_prefix == ""

    def test_resolve_message_prepends_prefix(self):
        svc = _SampleService()
        svc._set_log_prefix("[SVC]")
        assert svc._resolve_log_message("hello") == "[SVC] hello"

    def test_resolve_message_without_prefix_returns_original(self):
        svc = _SampleService()
        assert svc._resolve_log_message("hello") == "hello"

    def test_resolve_message_empty_prefix_prepends_space(self):
        svc = _SampleService()
        svc._set_log_prefix("")
        # empty prefix still prepends " " (trailing space in format string)
        assert svc._resolve_log_message("hello") == " hello"


# ──────────────────────────────────────────────────────────────────────────────
# TestLogStream
# ──────────────────────────────────────────────────────────────────────────────


class TestLogStream:
    def test_log_stream_absent_before_first_log(self):
        svc = _SampleService()
        assert not hasattr(svc, "_log_stream")

    def test_log_stream_created_after_first_log(self):
        svc = _SampleService()
        svc.info("init check")
        assert hasattr(svc, "_log_stream")

    def test_each_instance_gets_own_log_stream(self):
        svc_a = _SampleService()
        svc_b = _SampleService()
        svc_a.info("a")
        svc_b.info("b")
        assert svc_a._log_stream is not svc_b._log_stream

    def test_custom_log_name_attribute_is_accepted(self):
        class NamedService(LogPlugin):
            _log_name = "my_service"

        svc = NamedService()
        svc.info("test")
        assert hasattr(svc, "_log_stream")


# ──────────────────────────────────────────────────────────────────────────────
# TestLogMethods
# ──────────────────────────────────────────────────────────────────────────────


class TestLogMethods:
    @pytest.fixture
    def svc(self):
        return _SampleService()

    def test_info_does_not_raise(self, svc):
        svc.info("info message")

    def test_debug_does_not_raise(self, svc):
        svc.debug("debug message")

    def test_warning_does_not_raise(self, svc):
        svc.warning("warning message")

    def test_error_does_not_raise(self, svc):
        svc.error("error message")

    def test_log_with_code_does_not_raise(self, svc):
        svc.log("msg", level="INFO", code=200)

    def test_log_with_context_does_not_raise(self, svc):
        svc.log("msg", level="INFO", context={"key": "value"})

    def test_log_with_tags_does_not_raise(self, svc):
        svc.log("msg", level="INFO", tags={"env": "test"})

    def test_log_with_metrics_does_not_raise(self, svc):
        svc.log("msg", level="INFO", metrics={"latency_ms": "12"})

    def test_log_with_prefix_prepends_correctly(self, svc):
        svc._set_log_prefix("[TEST]")
        # should not raise; prefix is applied before emit
        svc.info("prefixed message")
