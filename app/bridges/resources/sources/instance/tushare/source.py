from __future__ import annotations

import json
from typing import Any

import polars as pl

from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.sources.base.factory import SourceFactory
from app.bridges.resources.sources.base.source import BaseSource
from app.bridges.resources.sources.instance.tushare.setting import TushareSourceSetting


@SourceFactory.register("tushare")
class TushareSource(BaseSource):
    """
    Tushare 数据源实现。

    实现 Tushare API 的数据获取逻辑，支持：
    - 自动拼接 fields 参数（逗号分隔）
    - Offset-based 分页（offset + limit）
    - 自适应停止（空页或部分页）

    Attributes:
        _setting_class: TushareSourceSetting 类

    Methods:
        build_params(params): 拼接 fields 参数
        _fetch_all(provider, params): Offset 分页循环获取

    Example:
        >>> source = TushareSource.from_yaml("items/tushare/tushare_stock_daily.yaml")
        >>> data = source.run(provider, {"trade_date": "20240101"})
        >>> print(data.columns)
        ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']

    """

    _setting_class = TushareSourceSetting

    def build_params(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        组装 Tushare API 参数。

        Tushare 特性：
        - fields 参数必须是逗号分隔的字符串（不是列表）
        - 如果 setting.fields 为空，则不传递 fields 参数（获取所有字段）

        Args:
            params: 运行时参数字典

        Returns:
            dict: 组装后的参数，可能包含 fields 字段

        Example:
            >>> # setting.fields = ["ts_code", "trade_date", "close"]
            >>> params = source.build_params({"trade_date": "20240101"})
            >>> print(params)
            {'trade_date': '20240101', 'fields': 'ts_code,trade_date,close'}

        """
        result = params.copy()
        if "include_fields" in self.setting.extra:
            result.pop("include_fields", None)
            field_names = ",".join(self.setting.field_names)
            result["fields"] = field_names
        return result

    def _fetch_all(
        self,
        provider: BaseProvider,
        params: dict[str, Any],
    ) -> pl.DataFrame:
        """
        分页获取 Tushare 数据。

        分页逻辑：
        1. 重置分页器（offset=0）
        2. 循环调用 API，每次传递 offset 和 limit
        3. 停止条件：
           - 返回 None 或空 DataFrame
           - 返回行数 < page_size（最后一页）
           - 达到 max_pages 限制
        4. 每次翻页后调用 coolant 限速

        Args:
            provider: Provider 实例
            params: 组装后的参数（来自 build_params）

        Returns:
            pl.DataFrame: 拼接后的完整数据，无数据时返回空 DataFrame

        Example:
            >>> # paginate: page_size=100, max_pages=5
            >>> data = source._fetch_all(provider, {"trade_date": "20240101"})
            >>> print(len(data))  # 可能是 234 行（3 页：100 + 100 + 34）
            234

        """
        self.paginate.reset()
        frames: list[pl.DataFrame] = []

        # 分页抓取数据
        for _ in range(self.paginate.max_pages):
            frame_params = params.copy()
            frame_params["offset"] = self.paginate.offset
            frame_params["limit"] = self.paginate.page_size
            frame_params_repr = json.dumps(
                frame_params,
                indent=4,
                ensure_ascii=False,
            )
            self.debug(f"_fetch_all: calling {self.setting.method}, params={frame_params_repr}")
            df = self._call_with_retry(
                provider=provider,
                method=self.setting.method,
                params=frame_params,
            )

            # 没有数据
            if df is None or df.is_empty():
                break

            frames.append(df)

            # 最后一页
            if len(df) < self.paginate.page_size:
                break

            # 翻页
            self.paginate.next()
            self.coolant.run()

        if frames:
            result = pl.concat(frames)
            del frames
            return result
        else:
            return pl.DataFrame()

    def transform(
        self,
        data: pl.DataFrame,
    ) -> pl.DataFrame:
        if data.is_empty():
            return data

        for field in self.setting.field_schemas:
            if field.name not in data.columns:
                continue

            # Date 类型：解析 + 格式化
            if field.type == "Date":
                data = data.with_columns(pl.col(field.name).str.to_date("%Y%m%d").dt.strftime("%Y-%m-%d"))

            # Float64 类型：强转（通常已正确，防御性代码）
            elif field.type == "Float64":
                data = data.with_columns(pl.col(field.name).cast(pl.Float64))

            # Int64 类型：强转
            elif field.type == "Int64":
                data = data.with_columns(pl.col(field.name).cast(pl.Int64))

            # Utf8 类型：强转字符串
            elif field.type == "Utf8":
                data = data.with_columns(pl.col(field.name).cast(pl.Utf8))

        return data
