from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING, Any

import polars as pl

from app.bridges.resources.cache import BridgesCache
from app.bridges.resources.strategies.base.factory import StrategyFactory
from app.bridges.resources.strategies.base.strategies import BaseStrategy

if TYPE_CHECKING:
    from app.bridges.resources.providers.base.provider import BaseProvider


@StrategyFactory.register("tushare", "by_tradedate")
class TushareByTradedate(BaseStrategy):
    """
    Tushare 按交易日展开策略。

    将包含 start_date 和 end_date 的参数展开为每个交易日的独立参数集。
    交易日历缓存 24 小时。

    Example:
        >>> params = {"start_date": "2024-01-01", "end_date": "2024-01-05"}
        >>> result = strategy.run(provider, params)
        >>> # [{"trade_date": "2024-01-02"}, {"trade_date": "2024-01-03"}, ...]

    """

    _METHOD = "trade_cal"
    _METHOD_PARAMS = {
        "exchange": "SSE",
        "is_open": 1,
    }
    _CACHE_KEY = "strategy_tushare_by_tradedate"
    _CACHE_TTL_HOURS = 24

    def __init__(self):
        super().__init__()
        self._set_log_prefix("TushareByTradedate()")

    def _resolve_date_value(
        self,
        value: str | None = None,
    ) -> date:
        if not value:
            return self._get_current_date()
        else:
            return self._read_date(value)

    def run(
        self,
        provider: BaseProvider,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        params = params.copy()
        start_date: str = params.get("start_date")
        end_date: str = params.get("end_date")
        start_date: date = self._resolve_date_value(start_date)
        end_date: date = self._resolve_date_value(end_date)
        all_dates: list[date] = self._get_stock_tradedates(
            provider=provider,
            start_date=start_date,
            end_date=end_date,
        )
        result = []
        params.pop("start_date", None)
        params.pop("end_date", None)
        for d in all_dates:
            payload = params.copy()
            payload["trade_date"] = d.strftime("%Y%m%d")
            result.append(payload)
        return result

    def _get_stock_tradedates(
        self,
        provider: BaseProvider,
        start_date: date,
        end_date: date,
    ) -> list[date]:
        method: str = self._METHOD
        method_params: dict[str, Any] = self._METHOD_PARAMS
        method_params_repr = json.dumps(
            method_params,
            indent=4,
            ensure_ascii=False,
        )
        cache: BridgesCache = provider.cache
        cache_key: str = self._CACHE_KEY

        # check cache
        if cache.check(self._CACHE_KEY):
            df: pl.DataFrame = cache.read(self._CACHE_KEY)
            self.debug("run: OK.")
            self.debug(f"run: {len(df)} rows from cache '{cache_key}'.")
        else:
            df: pl.DataFrame = provider.call(
                method=method,
                **method_params,
            )
            self.debug(f"run: {len(df)} rows from '{method}' call.")
            if df is None or df.is_empty():
                self.warning(f"run: no data returned from '{method}'.")
                self.debug(f"run: with params {method_params_repr}.")
                return []
            else:
                cache.write(
                    key=cache_key,
                    data=df,
                    ttl_hours=self._CACHE_TTL_HOURS,
                )
                self.debug("run: OK.")
                self.debug(f"run: {len(df)} rows write to cache '{cache_key}' .")

        # filter by start_date and end_date
        result = (
            df.with_columns(pl.col("cal_date").str.to_date("%Y%m%d"))
            .filter(pl.col("is_open") == 1)
            .filter(pl.col("cal_date").is_between(start_date, end_date))
            .select("cal_date")
            .to_series()
            .to_list()
        )
        return result
