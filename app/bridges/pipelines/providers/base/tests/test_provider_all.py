"""
综合测试：app.bridges.providers.base.provider

覆盖范围
--------
- TestInit      __init__ 正确从 setting 初始化字段，session 创建但未连接
- TestAbstract  未实现任意一个抽象方法时无法实例化
- TestDescribe  describe() 返回合法 JSON 字符串，内容与 export() 一致
- TestJit       jit() 在 enabled/disabled 两种状态下的行为
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from app.bridges.pipelines.providers.base.provider import BaseProvider
from app.bridges.pipelines.providers.base.session import BaseSession
from app.common.setting.bridges import BaseProviderSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


_MOCK_SETTING = BaseProviderSetting(name="mock", type="mock-type", region="hk", use_cache=False)


class _MockSession(BaseSession):
    def _create_session(self) -> str:
        return "mock-handle"


class _MockProvider(BaseProvider):
    def _resolve_setting(self, name: str) -> BaseProviderSetting:
        return _MOCK_SETTING

    def _create_session(self) -> _MockSession:
        return _MockSession(setting=self.setting)

    def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        return method

    def export(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "region": self.region}


# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    def test_type_set_from_setting(self):
        p = _MockProvider("mock")
        assert p.type == "mock-type"

    def test_name_set_from_setting(self):
        p = _MockProvider("mock")
        assert p.name == "mock"

    def test_region_set_from_setting(self):
        p = _MockProvider("mock")
        assert p.region == "hk"

    def test_use_cache_set_from_setting(self):
        p = _MockProvider("mock")
        assert p.use_cache is False

    def test_session_is_basesession_instance(self):
        p = _MockProvider("mock")
        assert isinstance(p._session, BaseSession)

    def test_session_not_connected_on_init(self):
        p = _MockProvider("mock")
        assert not p._session.is_ready()

    def test_each_instance_has_own_session(self):
        p1 = _MockProvider("mock")
        p2 = _MockProvider("mock")
        assert p1._session is not p2._session


# ──────────────────────────────────────────────────────────────────────────────
# TestAbstract
# ──────────────────────────────────────────────────────────────────────────────


class TestAbstract:
    def test_cannot_instantiate_base_provider_directly(self):
        with pytest.raises(TypeError):
            BaseProvider("mock")

    def test_missing_create_session_raises(self):
        class _NoSession(BaseProvider):
            def call(self, method, *args, **kwargs):
                return None

            def export(self):
                return {}

        with pytest.raises(TypeError):
            _NoSession("mock")

    def test_missing_call_raises(self):
        class _NoCall(BaseProvider):
            def _create_session(self):
                return _MockSession(setting=_MOCK_SETTING)

            def export(self):
                return {}

        with pytest.raises(TypeError):
            _NoCall("mock")

    def test_missing_export_raises(self):
        class _NoExport(BaseProvider):
            def _create_session(self):
                return _MockSession(setting=_MOCK_SETTING)

            def call(self, method, *args, **kwargs):
                return None

        with pytest.raises(TypeError):
            _NoExport("mock")


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_describe_returns_string(self):
        p = _MockProvider("mock")
        assert isinstance(p.describe(), str)

    def test_describe_is_valid_json(self):
        p = _MockProvider("mock")
        parsed = json.loads(p.describe())
        assert isinstance(parsed, dict)

    def test_describe_content_matches_export(self):
        p = _MockProvider("mock")
        parsed = json.loads(p.describe())
        assert parsed == p.export()

    def test_describe_contains_name(self):
        p = _MockProvider("mock")
        parsed = json.loads(p.describe())
        assert parsed["name"] == "mock"


# ──────────────────────────────────────────────────────────────────────────────
# TestJit
# ──────────────────────────────────────────────────────────────────────────────


class TestJit:
    def test_jit_does_not_sleep_when_disabled(self):
        p = _MockProvider("mock")
        # jitter is disabled by default (no jitter settings in _MOCK_SETTING)
        with patch("app.bridges.accessory.jitter.time.sleep") as mock_sleep:
            p.jit()
            mock_sleep.assert_not_called()

    def test_jit_calls_sleep_when_enabled(self):
        from app.bridges.accessory.jitter import Jitter

        p = _MockProvider("mock")
        p.jitter = Jitter(min_seconds=0.1, max_seconds=0.2)
        with patch("app.bridges.accessory.jitter.time.sleep") as mock_sleep:
            p.jit()
            mock_sleep.assert_called_once()
