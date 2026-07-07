"""
综合测试：resources.connections.base.connection

覆盖范围
--------
- TestBaseConnection   抽象约束、get_connection 懒加载单例、connect / close / is_connected
"""

from __future__ import annotations

from typing import Any

import pytest

from app.bridges.resources.connections.base.connection import BaseConnection
from app.common.setting.connections import OssConnectionSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_OSS_SETTING = OssConnectionSetting(
    name="test_conn",
    type="oss",
    access_key_id="test_access_key",
    access_key_secret="test_secret_key",
    endpoint="oss-cn-test.aliyuncs.com",
    region="cn-test",
    bucket="test-bucket",
)


class _CountingConnection(BaseConnection):
    """每次 _create_connection 返回递增整数，方便区分新旧实例。"""

    def __init__(self) -> None:
        self._counter = 0
        super().__init__(setting=_OSS_SETTING)

    def _create_connection(self) -> int:
        self._counter += 1
        return self._counter

    def ping(self) -> bool:
        return True


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseConnection
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseConnection:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseConnection(setting=_OSS_SETTING)

    def test_missing_create_connection_raises(self):
        class _NoPing(BaseConnection):
            def _create_connection(self) -> Any:
                return "handle"

        with pytest.raises(TypeError):
            _NoPing(setting=_OSS_SETTING)

    def test_missing_ping_raises(self):
        class _NoCreate(BaseConnection):
            def ping(self) -> bool:
                return True

        with pytest.raises(TypeError):
            _NoCreate(setting=_OSS_SETTING)

    def test_connection_is_none_on_init(self):
        c = _CountingConnection()
        assert c._connection is None

    def test_is_connected_false_before_connect(self):
        c = _CountingConnection()
        assert c.is_connected is False

    def test_is_connected_true_after_connect(self):
        c = _CountingConnection()
        c.connect()
        assert c.is_connected is True

    def test_get_connection_creates_on_first_call(self):
        c = _CountingConnection()
        handle = c.get_connection()
        assert handle == 1

    def test_get_connection_returns_same_instance_on_second_call(self):
        c = _CountingConnection()
        assert c.get_connection() is c.get_connection()

    def test_get_connection_does_not_recreate(self):
        c = _CountingConnection()
        c.get_connection()
        c.get_connection()
        assert c._counter == 1

    def test_close_resets_connection_to_none(self):
        c = _CountingConnection()
        c.connect()
        c.close()
        assert c._connection is None

    def test_close_sets_is_connected_false(self):
        c = _CountingConnection()
        c.connect()
        c.close()
        assert c.is_connected is False

    def test_reconnects_after_close(self):
        c = _CountingConnection()
        c.connect()
        c.close()
        handle = c.get_connection()
        assert handle == 2

    def test_name_from_setting(self):
        assert _CountingConnection().name == "test_conn"

    def test_type_from_setting(self):
        assert _CountingConnection().type == "oss"

    def test_export_contains_name(self):
        assert _CountingConnection().export()["name"] == "test_conn"

    def test_export_contains_type(self):
        assert _CountingConnection().export()["type"] == "oss"

    def test_export_contains_is_connected(self):
        c = _CountingConnection()
        assert "is_connected" in c.export()

    def test_export_is_connected_reflects_state(self):
        c = _CountingConnection()
        assert c.export()["is_connected"] is False
        c.connect()
        assert c.export()["is_connected"] is True

    def test_describe_returns_valid_json(self):
        import json

        result = json.loads(_CountingConnection().describe())
        assert isinstance(result, dict)
