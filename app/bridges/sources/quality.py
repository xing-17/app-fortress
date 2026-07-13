from __future__ import annotations

import json
from typing import Any

import polars as pl


class SourceQuality:
    """
    单次 Source 运行的数据质量快照。

    使用 Polars 单遍计算生成数据质量报告，不产生原始数据的额外拷贝。
    计算数据集、主键、行和列级别的质量指标。

    质量维度：
        - 数据级别：行数、列数、是否为空、近似大小
        - 主键级别：去重数、重复数/率、空值数/率
        - 行级别：完整行去重数、重复行数/率
        - 列级别：每列的类型、去重数/率、空值数/率、是否主键

    Attributes:
        source_name (str): 数据源名称
        source_context_id (str): 数据源上下文 ID
        extra (dict[str, Any]): 额外信息，如执行状态、时间戳

        data_is_empty (bool): 数据是否为空
        data_size_height (int): 数据行数
        data_size_width (int): 数据列数
        data_approx_bytes (int): 数据近似大小（字节）

        primary_keys (list[str]): 主键字段列表（过滤后实际存在的）
        primary_distinct_count (int): 主键去重后的行数
        primary_distinct_rate (float): 主键去重率（0-1）
        primary_duplicate_count (int): 主键重复的行数
        primary_duplicate_rate (float): 主键重复率（0-1）
        primary_null_count (int): 主键字段的空值总数
        primary_null_rate (float): 主键字段的空值率（0-1）

        row_distinct_count (int): 完整行去重后的行数
        row_distinct_rate (float): 完整行去重率（0-1）
        row_duplicates (int): 重复的完整行数
        row_duplicates_rate (float): 完整行重复率（0-1）

        columns (dict[str, dict]): 列级别指标，每列包含：
            - type (str): 列数据类型
            - is_primary (bool): 是否为主键字段
            - distinct_count (int): 去重后的值数量
            - distinct_rate (float): 去重率（0-1）
            - null_count (int): 空值数量
            - null_rate (float): 空值率（0-1）

    Methods:
        report() -> pl.DataFrame:
            生成 Polars DataFrame 格式的质量报告。
            每列生成一行，包含所有质量指标。

        export() -> dict[str, Any]:
            导出为字典格式，包含所有质量信息。

        describe() -> str:
            返回 JSON 格式的质量报告字符串。

    Example:
        >>> df = pl.DataFrame({
        ...     "ts_code": ["000001.SZ", "000002.SZ", "000002.SZ"],
        ...     "trade_date": ["20240101", "20240101", "20240102"],
        ...     "close": [10.5, 20.3, None],
        ... })
        >>> quality = SourceQuality(
        ...     source_name="daily_basic",
        ...     source_context_id="sctx_abc123",
        ...     data=df,
        ...     primary_keys=["ts_code", "trade_date"],
        ...     extra={"status": "SUCCESS"},
        ... )
        >>> print(f"Rows: {quality.data_size_height}")
        >>> print(f"PK Duplicates: {quality.primary_duplicate_count}")
        >>> print(quality.describe())

    """

    def __init__(
        self,
        source_name: str,  # source name
        source_context_id: str,  # source context id
        data: pl.DataFrame = pl.DataFrame(),
        primary_keys: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.source_name = source_name
        self.source_context_id = source_context_id
        self._pks = self._resolve_pks(data, primary_keys)
        self.extra = extra or {}
        self.data_is_empty = data.is_empty()
        self.data_size_height = data.height
        self.data_size_width = data.width
        self.data_approx_bytes = data.estimated_size()

        # Get primary key insights
        pk_denom = data.height * len(self._pks)
        if self.data_is_empty or not self._pks:
            self.primary_keys = []
            self.primary_distinct_count = 0
            self.primary_distinct_rate = 0.0
            self.primary_duplicate_count = 0
            self.primary_duplicate_rate = 0.0
            self.primary_null_count = 0
            self.primary_null_rate = 0.0
        else:
            self.primary_keys = self._pks
            self.primary_distinct_count = data.select(self.primary_keys).unique().height
            self.primary_distinct_rate = round(self.primary_distinct_count / data.height, 4)
            self.primary_duplicate_count = data.height - self.primary_distinct_count
            self.primary_duplicate_rate = round(self.primary_duplicate_count / data.height, 4)
            self.primary_null_count = sum(data.select(self.primary_keys).null_count().to_series())
            if pk_denom > 0:
                self.primary_null_rate = round(self.primary_null_count / pk_denom, 4)
            else:
                self.primary_null_rate = 0.0

        # Get row level insights
        if self.data_is_empty:
            self.row_distinct_count = 0
            self.row_distinct_rate = 0.0
            self.row_duplicates = 0
            self.row_duplicates_rate = 0.0
        else:
            self.row_distinct_count = data.unique().height
            self.row_distinct_rate = round(self.row_distinct_count / data.height, 4)
            self.row_duplicates = data.height - self.row_distinct_count
            self.row_duplicates_rate = round(self.row_duplicates / data.height, 4)

        # Get column level insights
        self.columns = {}
        null_df = data.null_count()
        distinct_df = data.select(pl.all().n_unique())
        denom = self.data_size_height
        for col in data.columns:
            null_count = int(null_df[col][0])
            distinct_count = int(distinct_df[col][0])
            self.columns[col] = {
                "type": str(data[col].dtype),
                "is_primary": col in self.primary_keys,
                "distinct_count": distinct_count,
                "distinct_rate": round(distinct_count / denom, 4),
                "null_count": null_count,
                "null_rate": round(null_count / denom, 4),
            }

    def _resolve_pks(
        self,
        data: pl.DataFrame,
        primary_keys: list[str] | None = None,
    ) -> list[str]:
        pks = []
        if primary_keys is not None:
            for k in primary_keys:
                if k in data.columns:
                    pks.append(k)
        return pks

    def report(self) -> pl.DataFrame:
        df_metrics: dict[str, Any] = {
            "source_name": self.source_name,
            "source_context_id": self.source_context_id,
            "data_is_empty": self.data_is_empty,
            "data_size_height": self.data_size_height,
            "data_size_width": self.data_size_width,
            "data_approx_bytes": self.data_approx_bytes,
            "primary_distinct_count": self.primary_distinct_count,
            "primary_distinct_rate": self.primary_distinct_rate,
            "primary_duplicate_count": self.primary_duplicate_count,
            "primary_duplicate_rate": self.primary_duplicate_rate,
            "primary_null_count": self.primary_null_count,
            "primary_null_rate": self.primary_null_rate,
            "row_distinct_count": self.row_distinct_count,
            "row_distinct_rate": self.row_distinct_rate,
            "row_duplicates": self.row_duplicates,
            "row_duplicates_rate": self.row_duplicates_rate,
        }
        col_fields: set[str] = {
            "column_name",
            "column_type",
            "is_primary",
            "distinct_count",
            "distinct_rate",
            "null_count",
            "null_rate",
        }

        # Check for conflicts between extra fields and reserved fields
        reserved_fields = set(df_metrics) | col_fields
        conflicts = reserved_fields.intersection(self.extra)
        if conflicts:
            raise ValueError(f"Extra conflict with reserved: {conflicts}")

        # Build the report DataFrame for each column
        rows = []
        for col, metrics in self.columns.items():
            row = {
                **self.extra,
                **df_metrics,
                "column_name": col,
                "column_type": metrics["type"],
                "is_primary": metrics["is_primary"],
                "distinct_count": metrics["distinct_count"],
                "distinct_rate": metrics["distinct_rate"],
                "null_count": metrics["null_count"],
                "null_rate": metrics["null_rate"],
            }
            rows.append(row)

        return pl.DataFrame(rows)

    def export(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_context_id": self.source_context_id,
            "extra": self.extra,
            "data": {
                "is_empty": self.data_is_empty,
                "height": self.data_size_height,
                "width": self.data_size_width,
                "approx_bytes": self.data_approx_bytes,
            },
            "primary_keys": {
                "keys": self.primary_keys,
                "distinct_count": self.primary_distinct_count,
                "distinct_rate": self.primary_distinct_rate,
                "duplicate_count": self.primary_duplicate_count,
                "duplicate_rate": self.primary_duplicate_rate,
                "null_count": self.primary_null_count,
                "null_rate": self.primary_null_rate,
            },
            "rows": {
                "distinct_count": self.row_distinct_count,
                "distinct_rate": self.row_distinct_rate,
                "duplicates": self.row_duplicates,
                "duplicates_rate": self.row_duplicates_rate,
            },
            "columns": self.columns,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
