from __future__ import annotations

from typing import Any

import pandas as pd
import polars as pl

from app.bridges.pipelines.providers.base.factory import ProviderFactory
from app.bridges.pipelines.providers.base.provider import BaseProvider
from app.bridges.pipelines.providers.tushare.session import TushareSession


@ProviderFactory.register("tushare")
class TushareProvider(
    BaseProvider,
):
    """
    Tushare 数据提供者。

    通过 Tushare Pro API 获取中国 A 股市场数据，支持股票、指数、基金等
    多种金融数据的查询。返回结果自动转换为 polars DataFrame 格式。

    Attributes:
        继承自 BaseProvider 的所有属性

    Example:
        >>> provider = TushareProvider(name="tushare-main")
        >>> df = provider.call("daily", ts_code="000001.SZ", start_date="20240101")
        >>> print(df.head())

    Notes:
        - 所有 API 调用都会自动执行 jitter 延迟
        - 返回 None 或空 DataFrame 时会记录 debug 日志
        - API 调用异常会抛出 RuntimeError
    """

    def __init__(
        self,
        name: str,
    ) -> None:
        super().__init__(name=name)
        self._set_log_prefix(f"TushareProvider({self.name})")

    def _create_session(self) -> TushareSession:
        return TushareSession(setting=self.setting)

    def call(
        self,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> None | pl.DataFrame:
        conn = self._session.get_session()
        api = getattr(conn, method, None)
        if api is None:
            raise ValueError(f"Method '{method}' not found in Tushare.")
        if not callable(api):
            raise ValueError(f"'{method}' is not callable in Tushare.")
        try:
            result: pd.DataFrame | None = api(
                *args,
                **kwargs,
            )
            self.jit()
            if result is None:
                self.debug(f"call: '{method}' returned None.")
                return None
            elif result.empty:
                self.debug(f"call: '{method}' returned empty DataFrame.")
                return pl.DataFrame()
            else:
                self.debug(f"call: '{method}' returned {len(result)} rows.")
                return pl.from_pandas(result)
        except Exception as e:
            raise RuntimeError(f"Error calling Tushare api '{method}': {e}") from e

    def export(self) -> dict[str, Any]:
        return {
            "setting": self.setting.export(),
            "session": self._session.export(),
        }
