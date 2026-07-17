"""
综合测试：app.bridges.resources.providers.tushare.provider

覆盖范围
--------
- TestInit           __init__ 正确初始化 TushareProvider
- TestCreateSession  _create_session 返回 TushareSession 实例
- TestCall          call() 正确调用 API 并返回 polars DataFrame
- TestCallEdgeCases call() 处理 None 和空 DataFrame 情况
- TestCallError     call() 正确处理异常
- TestExport        export() 返回正确的结构
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import polars as pl
import pytest

from app.bridges.resources.providers.tushare.provider import TushareProvider
from app.bridges.resources.providers.tushare.session import TushareSession
from app.common.setting.bridges import TushareProviderSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


_MOCK_SETTING = TushareProviderSetting(
    name="test-tushare",
    type="tushare",
    region="cn",
    secret="test-token",
    timeout=60,
    use_cache=False,
)


@pytest.fixture
def mock_provider():
    """返回一个 mock 了 setting 和 session 的 TushareProvider"""
    with patch.object(TushareProvider, "_resolve_setting", return_value=_MOCK_SETTING):
        with patch.object(TushareProvider, "_create_session") as mock_create:
            mock_session = MagicMock(spec=TushareSession)
            mock_create.return_value = mock_session
            provider = TushareProvider(name="test-tushare")
            yield provider


# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    @patch.object(TushareProvider, "_resolve_setting", return_value=_MOCK_SETTING)
    @patch.object(TushareProvider, "_create_session")
    def test_name_set_from_setting(self, mock_create, mock_resolve):
        mock_create.return_value = MagicMock(spec=TushareSession)
        provider = TushareProvider(name="test-tushare")
        assert provider.name == "test-tushare"

    @patch.object(TushareProvider, "_resolve_setting", return_value=_MOCK_SETTING)
    @patch.object(TushareProvider, "_create_session")
    def test_type_set_from_setting(self, mock_create, mock_resolve):
        mock_create.return_value = MagicMock(spec=TushareSession)
        provider = TushareProvider(name="test-tushare")
        assert provider.type == "tushare"

    @patch.object(TushareProvider, "_resolve_setting", return_value=_MOCK_SETTING)
    @patch.object(TushareProvider, "_create_session")
    def test_region_set_from_setting(self, mock_create, mock_resolve):
        mock_create.return_value = MagicMock(spec=TushareSession)
        provider = TushareProvider(name="test-tushare")
        assert provider.region == "cn"


# ──────────────────────────────────────────────────────────────────────────────
# TestCreateSession
# ──────────────────────────────────────────────────────────────────────────────


class TestCreateSession:
    @patch.object(TushareProvider, "_resolve_setting", return_value=_MOCK_SETTING)
    @patch("app.bridges.resources.providers.tushare.provider.TushareSession")
    def test_create_session_returns_tushare_session(self, mock_session_class, mock_resolve):
        mock_session_instance = MagicMock(spec=TushareSession)
        mock_session_class.return_value = mock_session_instance

        provider = TushareProvider(name="test-tushare")

        mock_session_class.assert_called_once_with(setting=_MOCK_SETTING)
        assert provider._session is mock_session_instance


# ──────────────────────────────────────────────────────────────────────────────
# TestCall
# ──────────────────────────────────────────────────────────────────────────────


class TestCall:
    def test_call_returns_polars_dataframe(self, mock_provider):
        # 准备 mock API
        mock_api = MagicMock()
        mock_df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        mock_api.daily.return_value = mock_df
        mock_provider._session.get_session.return_value = mock_api

        # 调用
        result = mock_provider.call("daily", ts_code="000001.SZ")

        # 验证
        assert isinstance(result, pl.DataFrame)
        assert result.shape == (2, 2)
        assert result.columns == ["col1", "col2"]

    def test_call_invokes_correct_api_method(self, mock_provider):
        mock_api = MagicMock()
        mock_df = pd.DataFrame({"col": [1]})
        mock_api.trade_cal.return_value = mock_df
        mock_provider._session.get_session.return_value = mock_api

        mock_provider.call("trade_cal", exchange="SSE")

        mock_api.trade_cal.assert_called_once_with(exchange="SSE")

    def test_call_passes_args_and_kwargs(self, mock_provider):
        mock_api = MagicMock()
        mock_df = pd.DataFrame({"col": [1]})
        mock_api.my_method.return_value = mock_df
        mock_provider._session.get_session.return_value = mock_api

        mock_provider.call("my_method", "arg1", "arg2", key1="val1", key2="val2")

        mock_api.my_method.assert_called_once_with("arg1", "arg2", key1="val1", key2="val2")


# ──────────────────────────────────────────────────────────────────────────────
# TestCallEdgeCases
# ──────────────────────────────────────────────────────────────────────────────


class TestCallEdgeCases:
    def test_call_returns_none_when_api_returns_none(self, mock_provider):
        mock_api = MagicMock()
        mock_api.daily.return_value = None
        mock_provider._session.get_session.return_value = mock_api

        result = mock_provider.call("daily")

        assert result is None

    def test_call_returns_empty_dataframe_when_api_returns_empty(self, mock_provider):
        mock_api = MagicMock()
        mock_api.daily.return_value = pd.DataFrame()
        mock_provider._session.get_session.return_value = mock_api

        result = mock_provider.call("daily")

        assert isinstance(result, pl.DataFrame)
        assert result.is_empty()


# ──────────────────────────────────────────────────────────────────────────────
# TestCallError
# ──────────────────────────────────────────────────────────────────────────────


class TestCallError:
    def test_call_raises_when_method_not_found(self, mock_provider):
        mock_api = MagicMock(spec=[])
        mock_provider._session.get_session.return_value = mock_api

        with pytest.raises(ValueError, match="Method 'nonexistent' not found"):
            mock_provider.call("nonexistent")

    def test_call_raises_when_method_not_callable(self, mock_provider):
        mock_api = MagicMock()
        mock_api.not_callable = "I am a string"
        mock_provider._session.get_session.return_value = mock_api

        with pytest.raises(ValueError, match="'not_callable' is not callable"):
            mock_provider.call("not_callable")

    def test_call_raises_runtime_error_on_api_exception(self, mock_provider):
        mock_api = MagicMock()
        mock_api.daily.side_effect = Exception("API Error")
        mock_provider._session.get_session.return_value = mock_api

        with pytest.raises(RuntimeError, match="Error calling Tushare api 'daily'"):
            mock_provider.call("daily")


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self, mock_provider):
        # Mock session export, but let setting.export() call the real method
        mock_provider._session.export = MagicMock(return_value={"status": "ready"})

        result = mock_provider.export()

        assert isinstance(result, dict)
        assert "setting" in result
        assert "session" in result

    def test_export_includes_setting_and_session(self, mock_provider):
        # Mock session export, but let setting.export() call the real method
        session_data = {"ready": True}
        mock_provider._session.export = MagicMock(return_value=session_data)

        result = mock_provider.export()

        assert result["setting"] == mock_provider.setting.export()
        assert result["session"] == session_data
