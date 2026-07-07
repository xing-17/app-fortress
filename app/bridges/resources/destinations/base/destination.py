from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import dlt
import polars as pl
import pyarrow as pa
from dlt.common.schema import TTableSchema

from app.bridges.resources.connections.base.connection import BaseConnection
from app.common.core.setting import GlobalSetting
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)
from app.common.setting.bridges import BridgesDestinationSetting


class BaseDestination(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
    ABC,
):
    """
    数据写出目标基类。

    定义 bridges 层写出的通用接口与生命周期管理。子类须实现 write() 和 export()。

    通过 as_dlt_destination() 将写出逻辑包装为 dlt Destination 对象，
    由 dlt pipeline 负责调用，并获得增量状态管理和 schema 演进能力。

    Attributes:
        setting:    Destination 配置（来自 bridges.yml destinations）
        name:       实例标识名，来自 setting.name
        connection: 底层连接对象（由 DestinationFactory 注入，可跨实例共享）

    Example:
        >>> @DestinationFactory.register("oss")
        ... class OSSDestination(BaseDestination):
        ...     def write(self, df, table_name, partition_col, partition_prefix): ...
        ...     def export(self) -> dict: ...
        >>> dest = OSSDestination(name="oss_prod_tushare", connection=conn)
        >>> dlt_dest = dest.as_dlt_destination(
        ...     partition_col="trade_date",
        ...     partition_prefix="date",
        ... )
        >>> pipeline = dlt.pipeline(destination=dlt_dest)

    """

    def __init__(
        self,
        name: str,
        connection: BaseConnection,
    ) -> None:
        super().__init__()
        self.setting: BridgesDestinationSetting = self._resolve_setting(name)
        self.name: str = self.setting.name
        self.connection: BaseConnection = connection
        self._set_log_prefix(f"{self.__class__.__name__}({self.name})")

    def _resolve_setting(
        self,
        name: str,
    ) -> BridgesDestinationSetting:
        bridges_setting = GlobalSetting.bridges
        return bridges_setting.get_destination(name=name)

    @abstractmethod
    def write(
        self,
        df: pl.DataFrame,
        table_name: str,
        partition_col: str,
        partition_prefix: str,
    ) -> None:
        raise NotImplementedError

    def as_dlt_destination(
        self,
        partition_col: str,
        partition_prefix: str,
    ) -> Any:
        dest_self = self

        @dlt.destination(
            name="fortress_parquet",
            batch_size=100_000,
            loader_file_format="parquet",
        )
        def _dlt_write(
            items: pa.Table,
            table: TTableSchema,
        ) -> None:
            dest_self.write(
                df=pl.from_arrow(items),
                table_name=table["name"],
                partition_col=partition_col,
                partition_prefix=partition_prefix,
            )

        return _dlt_write()

    @abstractmethod
    def export(self) -> dict[str, Any]:
        raise NotImplementedError

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
