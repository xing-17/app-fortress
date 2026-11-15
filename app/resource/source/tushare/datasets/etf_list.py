from __future__ import annotations

from typing import ClassVar

import polars as pl

from app.internal.model.definition.desc import ColumnDesc
from app.resource.accessory.paginate.paginate import Paginate
from app.resource.source.tushare.dataset import TushareDataset


class ETFListDataset(TushareDataset):
    """
    Tushare ETF list dataset, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "etf_list"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        method (str):
            Tushare API method name, fixed to "etf_basic"
        paginate (Paginate):
            Pagination configuration, 5000 rows per page and at most 10 pages

    Methods:
    ----------
        transform(df: pl.DataFrame) -> pl.DataFrame:
            Parse `setup_date` and `list_date` into dates and add `snapshotdate`.

    """

    name: ClassVar[str] = "etf_list"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    description: ClassVar[str] = "Dataset for Tushare ETF list."
    column_descs: ClassVar[list[ColumnDesc]] = [
        ColumnDesc(
            name="ts_code",
            description="基金交易代码",
        ),
        ColumnDesc(
            name="csname",
            description="ETF中文简称",
        ),
        ColumnDesc(
            name="extname",
            description="ETF扩位简称(对应交易所简称)",
        ),
        ColumnDesc(
            name="cname",
            description="基金中文全称",
        ),
        ColumnDesc(
            name="index_code",
            description="ETF基准指数代码",
        ),
        ColumnDesc(
            name="index_name",
            description="ETF基准指数中文全称",
        ),
        ColumnDesc(
            name="setup_date",
            description="设立日期",
        ),
        ColumnDesc(
            name="list_date",
            description="上市日期",
        ),
        ColumnDesc(
            name="list_status",
            description="存续状态(L上市 D退市 P待上市)",
        ),
        ColumnDesc(
            name="exchange",
            description="交易所(上交所SH 深交所SZ)",
        ),
        ColumnDesc(
            name="mgr_name",
            description="基金管理人简称",
        ),
        ColumnDesc(
            name="custod_name",
            description="基金托管人名称",
        ),
        ColumnDesc(
            name="mgt_fee",
            description="基金管理人收取的费用",
        ),
        ColumnDesc(
            name="etf_type",
            description="ETF类型",
        ),
        ColumnDesc(
            name="snapshotdate",
            description="数据快照日期，即抓取当天的日期",
        ),
    ]
    origin: ClassVar[list[str]] = [
        "ts_code",  # 基金交易代码
        "csname",  # ETF中文简称
        "extname",  # ETF扩位简称(对应交易所简称)
        "cname",  # 基金中文全称
        "index_code",  # ETF基准指数代码
        "index_name",  # ETF基准指数中文全称
        "setup_date",  # 设立日期(格式：YYYYMMDD)
        "list_date",  # 上市日期(格式：YYYYMMDD)
        "list_status",  # 存续状态(L上市 D退市 P待上市)
        "exchange",  # 交易所(上交所SH 深交所SZ)
        "mgr_name",  # 基金管理人简称
        "custod_name",  # 基金托管人名称
        "mgt_fee",  # 基金管理人收取的费用
        "etf_type",  # ETF类型
        # No snapshotdate in the original Tushare API response
    ]
    method: ClassVar[str] = "etf_basic"
    paginate: ClassVar[Paginate] = Paginate(
        page_size=5000,
        end_page=10,
    )
    # [Inherited] jitter: ClassVar[Jitter]
    # [Inherited] coolant: ClassVar[Coolant]
    # [Inherited] retry: ClassVar[Retry]

    def transform(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        df: pl.DataFrame = self._col_format_date_value(
            df,
            cols=["setup_date", "list_date"],
        )
        df: pl.DataFrame = self._col_add_snapshotdate(df)
        return df
