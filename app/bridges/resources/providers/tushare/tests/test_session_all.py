"""
综合测试：app.bridges.resources.providers.tushare.session

覆盖范围
--------
- TestInit      __init__ 正确初始化 TushareSession
- TestCreate    _create_session 返回有效的 tushare.pro_api 实例
- TestConnect   连接后 session 可用
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.bridges.resources.providers.tushare.session import TushareSession
from app.common.setting.bridges import TushareProviderSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


def _make_setting(
    name: str = "test-tushare",
    secret: str = "test-token",
    timeout: int = 60,
    ttl_seconds: int | None = None,
) -> TushareProviderSetting:
    return TushareProviderSetting(
        name=name,
        type="tushare",
        secret=secret,
        timeout=timeout,
        ttl_seconds=ttl_seconds,
    )


# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    def test_name_set_from_setting(self):
        setting = _make_setting(name="my-tushare")
        session = TushareSession(setting=setting)
        assert session.name == "my-tushare"

    def test_session_not_connected_initially(self):
        setting = _make_setting()
        session = TushareSession(setting=setting)
        assert not session.is_ready()


# ──────────────────────────────────────────────────────────────────────────────
# TestCreate
# ──────────────────────────────────────────────────────────────────────────────


class TestCreate:
    @patch("app.bridges.resources.providers.tushare.session.tushare.pro_api")
    def test_create_session_calls_pro_api_with_token(self, mock_pro_api):
        mock_api = MagicMock()
        mock_pro_api.return_value = mock_api

        setting = _make_setting(secret="my-secret-token", timeout=120)
        session = TushareSession(setting=setting)
        session.connect()

        mock_pro_api.assert_called_once_with(
            token="my-secret-token",
            timeout=120,
        )

    @patch("app.bridges.resources.providers.tushare.session.tushare.pro_api")
    def test_create_session_returns_api_instance(self, mock_pro_api):
        mock_api = MagicMock()
        mock_pro_api.return_value = mock_api

        setting = _make_setting()
        session = TushareSession(setting=setting)
        result = session._create_session()

        assert result is mock_api


# ──────────────────────────────────────────────────────────────────────────────
# TestConnect
# ──────────────────────────────────────────────────────────────────────────────


class TestConnect:
    @patch("app.bridges.resources.providers.tushare.session.tushare.pro_api")
    def test_connect_makes_session_ready(self, mock_pro_api):
        mock_api = MagicMock()
        mock_pro_api.return_value = mock_api

        setting = _make_setting()
        session = TushareSession(setting=setting)
        session.connect()

        assert session.is_ready()

    @patch("app.bridges.resources.providers.tushare.session.tushare.pro_api")
    def test_get_session_returns_api_instance(self, mock_pro_api):
        mock_api = MagicMock()
        mock_pro_api.return_value = mock_api

        setting = _make_setting()
        session = TushareSession(setting=setting)
        result = session.get_session()

        assert result is mock_api
