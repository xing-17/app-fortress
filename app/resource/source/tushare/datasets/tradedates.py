from __future__ import annotations

from typing import ClassVar

import polars as pl

from app.resource.accessory.paginate.paginate import Paginate
from app.resource.source.tushare.dataset import TushareDataset


class TradedateDataset(TushareDataset):
    """
    Tushare trade calendar dataset, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "tradedates"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        method (str):
            Tushare API method name, fixed to "trade_cal"
        paginate (Paginate):
            Pagination configuration, 5000 rows per page and at most 10 pages

    Methods:
    ----------
        transform(df: pl.DataFrame) -> pl.DataFrame:
            Parse `cal_date`/`pretrade_date` into dates, cast `is_open` to bool and add `snapshotdate`.

    """

    name: ClassVar[str] = "tradedates"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    description: ClassVar[str] = "Dataset for Tushare trade calendar."
    method: ClassVar[str] = "trade_cal"
    paginate: ClassVar[Paginate] = Paginate(
        page_size=5000,
        end_page=10,
    )
    # [Inherited] jitter: ClassVar[Jitter]
    # [Inherited] coolant: ClassVar[Coolant]
    # [Inherited] retry: ClassVar[Retry]

    origin: ClassVar[list[str]] = [
        "exchange",
        "cal_date",
        "is_open",
        "pretrade_date",
    ]

    def transform(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        df: pl.DataFrame = self._col_format_date_value(
            df,
            cols=["cal_date", "pretrade_date"],
        )
        df = self._col_ensure_bool_columns(
            df,
            cols=["is_open"],
        )
        df: pl.DataFrame = self._col_add_snapshotdate(df)
        return df
