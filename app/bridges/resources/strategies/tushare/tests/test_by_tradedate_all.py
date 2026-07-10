"""
综合测试：app.bridges.resources.strategies.tushare.by_tradedate

覆盖范围
--------
- TestInit             __init__ 正确设置 log prefix
- TestResolveDateValue _resolve_date_value() None 返回当前日期，有值时解析日期
- TestRun              run() 正确生成交易日参数列表
- TestGetStockTradedates _get_stock_tradedates() 缓存机制和日期过滤
- TestCache            缓存读写和 TTL 验证
- TestRegistration     验证策略已注册到 StrategyFactory
"""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock, patch

import polars as pl
import pytest

from app.bridges.resources.cache import BridgesCache
from app.bridges.resources.providers.tushare.provider import TushareProvider
from app.bridges.resources.strategies.base.factory import StrategyFactory
from app.bridges.resources.strategies.base.strategies import BaseStrategy
from app.bridges.resources.strategies.tushare.by_tradedate import TushareByTradedate

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_cache():
    """Mock BridgesCache"""
    cache = Mock(spec=BridgesCache)
    cache.check.return_value = False
    cache.read.return_value = pl.DataFrame()
    cache.write.return_value = None
    return cache


@pytest.fixture
def mock_provider(mock_cache):
    """Mock TushareProvider"""
    provider = Mock(spec=TushareProvider)
    provider.cache = mock_cache
    provider.call.return_value = pl.DataFrame(
        {
            "cal_date": ["20240101", "20240102", "20240103", "20240104", "20240105"],
            "is_open": [0, 1, 1, 0, 1],
        }
    )
    return provider


@pytest.fixture
def strategy():
    """TushareByTradedate 实例"""
    return TushareByTradedate()


# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    def test_init_inherits_base_strategy(self, strategy):
        """测试 TushareByTradedate 继承 BaseStrategy"""
        assert isinstance(strategy, BaseStrategy)

    def test_init_sets_log_prefix(self, strategy):
        """测试 __init__ 设置 log prefix"""
        assert hasattr(strategy, "debug")

    def test_init_has_cache_key(self, strategy):
        """测试类有缓存 key 常量"""
        assert hasattr(TushareByTradedate, "_CACHE_KEY")
        assert TushareByTradedate._CACHE_KEY == "strategy_tushare_by_tradedate"

    def test_init_has_cache_ttl(self, strategy):
        """测试类有缓存 TTL 常量"""
        assert hasattr(TushareByTradedate, "_CACHE_TTL_HOURS")
        assert TushareByTradedate._CACHE_TTL_HOURS == 24

    def test_init_has_method_config(self, strategy):
        """测试类有 API 方法配置"""
        assert hasattr(TushareByTradedate, "_METHOD")
        assert TushareByTradedate._METHOD == "trade_cal"
        assert hasattr(TushareByTradedate, "_METHOD_PARAMS")


# ──────────────────────────────────────────────────────────────────────────────
# TestResolveDateValue
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveDateValue:
    def test_resolve_none_returns_current_date(self, strategy):
        """测试 None 返回当前日期"""
        with patch.object(strategy, "_get_current_date") as mock_get_date:
            mock_get_date.return_value = date(2024, 1, 15)
            result = strategy._resolve_date_value(None)
            assert result == date(2024, 1, 15)
            mock_get_date.assert_called_once()

    def test_resolve_empty_string_returns_current_date(self, strategy):
        """测试空字符串返回当前日期"""
        with patch.object(strategy, "_get_current_date") as mock_get_date:
            mock_get_date.return_value = date(2024, 1, 15)
            result = strategy._resolve_date_value("")
            assert result == date(2024, 1, 15)

    def test_resolve_date_string(self, strategy):
        """测试解析日期字符串"""
        with patch.object(strategy, "_read_date") as mock_read_date:
            mock_read_date.return_value = date(2024, 1, 1)
            result = strategy._resolve_date_value("2024-01-01")
            assert result == date(2024, 1, 1)
            mock_read_date.assert_called_once_with("2024-01-01")


# ──────────────────────────────────────────────────────────────────────────────
# TestRun
# ──────────────────────────────────────────────────────────────────────────────


class TestRun:
    def test_run_returns_list_of_dicts(self, strategy, mock_provider):
        """测试 run() 返回字典列表"""
        params = {"start_date": "2024-01-01", "end_date": "2024-01-05"}
        with patch.object(strategy, "_get_stock_tradedates") as mock_get_dates:
            mock_get_dates.return_value = [date(2024, 1, 2), date(2024, 1, 3)]
            result = strategy.run(mock_provider, params)
            assert isinstance(result, list)
            assert all(isinstance(item, dict) for item in result)

    def test_run_generates_params_for_each_tradedate(self, strategy, mock_provider):
        """测试 run() 为每个交易日生成参数"""
        params = {"start_date": "2024-01-01", "end_date": "2024-01-05"}
        with patch.object(strategy, "_get_stock_tradedates") as mock_get_dates:
            mock_get_dates.return_value = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 5)]
            result = strategy.run(mock_provider, params)
            assert len(result) == 3

    def test_run_removes_start_end_date_from_params(self, strategy, mock_provider):
        """测试 run() 移除 start_date 和 end_date"""
        params = {"start_date": "2024-01-01", "end_date": "2024-01-05", "symbol": "600000"}
        with patch.object(strategy, "_get_stock_tradedates") as mock_get_dates:
            mock_get_dates.return_value = [date(2024, 1, 2)]
            result = strategy.run(mock_provider, params)
            assert "start_date" not in result[0]
            assert "end_date" not in result[0]
            assert "symbol" in result[0]

    def test_run_adds_trade_date_to_each_param(self, strategy, mock_provider):
        """测试 run() 为每个参数添加 trade_date"""
        params = {"start_date": "2024-01-01", "end_date": "2024-01-05"}
        with patch.object(strategy, "_get_stock_tradedates") as mock_get_dates:
            mock_get_dates.return_value = [date(2024, 1, 2), date(2024, 1, 3)]
            result = strategy.run(mock_provider, params)
            assert result[0]["trade_date"] == "20240102"
            assert result[1]["trade_date"] == "20240103"

    def test_run_preserves_other_params(self, strategy, mock_provider):
        """测试 run() 保留其他参数"""
        params = {"start_date": "2024-01-01", "end_date": "2024-01-05", "symbol": "600000", "exchange": "SSE"}
        with patch.object(strategy, "_get_stock_tradedates") as mock_get_dates:
            mock_get_dates.return_value = [date(2024, 1, 2)]
            result = strategy.run(mock_provider, params)
            assert result[0]["symbol"] == "600000"
            assert result[0]["exchange"] == "SSE"

    def test_run_does_not_mutate_input_params(self, strategy, mock_provider):
        """测试 run() 不修改输入参数"""
        params = {"start_date": "2024-01-01", "end_date": "2024-01-05", "symbol": "600000"}
        original_params = params.copy()
        with patch.object(strategy, "_get_stock_tradedates") as mock_get_dates:
            mock_get_dates.return_value = [date(2024, 1, 2)]
            strategy.run(mock_provider, params)
            assert params == original_params


# ──────────────────────────────────────────────────────────────────────────────
# TestGetStockTradedates
# ──────────────────────────────────────────────────────────────────────────────


class TestGetStockTradedates:
    def test_get_stock_tradedates_returns_list_of_dates(self, strategy, mock_provider):
        """测试 _get_stock_tradedates() 返回日期列表"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)
        result = strategy._get_stock_tradedates(mock_provider, start, end)
        assert isinstance(result, list)
        assert all(isinstance(d, date) for d in result)

    def test_get_stock_tradedates_filters_by_date_range(self, strategy, mock_provider):
        """测试日期范围过滤"""
        mock_provider.call.return_value = pl.DataFrame(
            {
                "cal_date": ["20240101", "20240102", "20240103", "20240105", "20240110"],
                "is_open": [1, 1, 1, 1, 1],
            }
        )
        start = date(2024, 1, 2)
        end = date(2024, 1, 5)
        result = strategy._get_stock_tradedates(mock_provider, start, end)
        assert len(result) == 3
        assert date(2024, 1, 2) in result
        assert date(2024, 1, 3) in result
        assert date(2024, 1, 5) in result
        assert date(2024, 1, 1) not in result
        assert date(2024, 1, 10) not in result

    def test_get_stock_tradedates_filters_open_days(self, strategy, mock_provider):
        """测试只返回交易日（is_open=1）"""
        mock_provider.call.return_value = pl.DataFrame(
            {
                "cal_date": ["20240101", "20240102", "20240103"],
                "is_open": [0, 1, 1],
            }
        )
        start = date(2024, 1, 1)
        end = date(2024, 1, 3)
        result = strategy._get_stock_tradedates(mock_provider, start, end)
        assert len(result) == 2
        assert date(2024, 1, 2) in result
        assert date(2024, 1, 3) in result
        assert date(2024, 1, 1) not in result


# ──────────────────────────────────────────────────────────────────────────────
# TestCache
# ──────────────────────────────────────────────────────────────────────────────


class TestCache:
    def test_cache_hit_skips_api_call(self, strategy, mock_provider, mock_cache):
        """测试缓存命中时跳过 API 调用"""
        mock_cache.check.return_value = True
        mock_cache.read.return_value = pl.DataFrame(
            {
                "cal_date": ["20240102", "20240103"],
                "is_open": [1, 1],
            }
        )
        start = date(2024, 1, 2)
        end = date(2024, 1, 3)
        strategy._get_stock_tradedates(mock_provider, start, end)
        mock_provider.call.assert_not_called()
        mock_cache.check.assert_called_once()
        mock_cache.read.assert_called_once()

    def test_cache_miss_calls_api(self, strategy, mock_provider, mock_cache):
        """测试缓存未命中时调用 API"""
        mock_cache.check.return_value = False
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)
        strategy._get_stock_tradedates(mock_provider, start, end)
        mock_provider.call.assert_called_once()

    def test_cache_writes_after_api_call(self, strategy, mock_provider, mock_cache):
        """测试 API 调用后写入缓存"""
        mock_cache.check.return_value = False
        mock_provider.call.return_value = pl.DataFrame(
            {
                "cal_date": ["20240102", "20240103"],
                "is_open": [1, 1],
            }
        )
        start = date(2024, 1, 2)
        end = date(2024, 1, 3)
        strategy._get_stock_tradedates(mock_provider, start, end)
        mock_cache.write.assert_called_once()

    def test_cache_write_uses_correct_key(self, strategy, mock_provider, mock_cache):
        """测试缓存使用正确的 key"""
        mock_cache.check.return_value = False
        mock_provider.call.return_value = pl.DataFrame(
            {
                "cal_date": ["20240102"],
                "is_open": [1],
            }
        )
        start = date(2024, 1, 2)
        end = date(2024, 1, 2)
        strategy._get_stock_tradedates(mock_provider, start, end)
        call_args = mock_cache.write.call_args
        assert call_args[1]["key"] == "strategy_tushare_by_tradedate"

    def test_cache_write_uses_correct_ttl(self, strategy, mock_provider, mock_cache):
        """测试缓存使用正确的 TTL"""
        mock_cache.check.return_value = False
        mock_provider.call.return_value = pl.DataFrame(
            {
                "cal_date": ["20240102"],
                "is_open": [1],
            }
        )
        start = date(2024, 1, 2)
        end = date(2024, 1, 2)
        strategy._get_stock_tradedates(mock_provider, start, end)
        call_args = mock_cache.write.call_args
        assert call_args[1]["ttl_hours"] == 24


# ──────────────────────────────────────────────────────────────────────────────
# TestRegistration
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistration:
    def test_strategy_is_registered(self):
        """测试策略已注册到工厂"""
        assert ("tushare", "by_tradedate") in StrategyFactory._registry

    def test_registered_class_is_correct(self):
        """测试注册的类是 TushareByTradedate"""
        assert StrategyFactory._registry[("tushare", "by_tradedate")] is TushareByTradedate

    def test_can_create_from_factory(self):
        """测试可以从工厂创建实例"""
        strategy = StrategyFactory.create(("tushare", "by_tradedate"))
        assert isinstance(strategy, TushareByTradedate)
        assert isinstance(strategy, BaseStrategy)
