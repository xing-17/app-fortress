from __future__ import annotations

import hashlib
import io
import posixpath

import oss2
import polars as pl

from app.bridges.connections.oss.connection import OSSConnection
from app.bridges.destinations.base.destination import BaseDestination
from app.bridges.destinations.base.factory import DestinationFactory


@DestinationFactory.register("oss")
class OSSDestination(BaseDestination):
    """
    OSS 写出目标。

    按 partition_col 列值分组写出，每组生成一个文件。
    写出格式由 setting.format 控制（parquet / csv），默认 parquet（snappy 压缩）。
    文件名为数据内容的 SHA-256 指纹（前 32 位），确保幂等写出。

    写出路径格式：
        {base_prefix}/{table_name}/{partition_prefix}={partition_val}/{fingerprint}.{ext}

    例：
        fortress/data/tushare/tushare_stock_capflow/date=2024-01-05/a3f9....parquet
        fortress/data/tushare/tushare_stock_profiles/snapshotdate=2024-01-05/b7c2....csv

    Attributes:
        connection: OSSConnection 实例（由工厂注入，可跨 destination 共享）

    Example:
        >>> dest = OSSDestination(name="oss_prod_tushare", connection=conn)
        >>> dlt_dest = dest.as_dlt_destination(
        ...     partition_col="trade_date",
        ...     partition_prefix="date",
        ... )
        >>> pipeline = dlt.pipeline(destination=dlt_dest)
        >>> pipeline.run(resource)

    """

    def __init__(
        self,
        name: str,
        connection: OSSConnection,
    ) -> None:
        super().__init__(
            name=name,
            connection=connection,
        )
        self._bucket: oss2.Bucket = connection.get_connection()
        self._base_prefix: str = self._resolve_prefix()

    def _resolve_prefix(self) -> str:
        return self.setting.base_prefix.strip("/")

    def _get_fingerprint(
        self,
        df: pl.DataFrame,
    ) -> str:
        df_sorted = df.select(sorted(df.columns))
        buf = io.BytesIO()
        df_sorted.write_parquet(buf)
        return hashlib.sha256(buf.getvalue()).hexdigest()[:32]

    def write(
        self,
        df: pl.DataFrame,
        table_name: str,
        partition_col: str,
        partition_prefix: str,
    ) -> None:
        if partition_col not in df.columns:
            raise ValueError(f"Partition column '{partition_col}' not found.")

        fmt = self.setting.format
        partition_vals = df[partition_col].unique().sort().to_list()
        for partition_val in partition_vals:
            partition_df = df.filter(pl.col(partition_col) == partition_val)
            fp = self._get_fingerprint(partition_df)
            path = posixpath.join(
                self._base_prefix,
                table_name,
                f"{partition_prefix}={partition_val}",
                f"{fp}.{fmt}",
            )
            self._write_file(df=partition_df, path=path, fmt=fmt)
            self.debug(f"write: {len(partition_df)} rows → {path} OK.")

    def _write_file(
        self,
        df: pl.DataFrame,
        path: str,
        fmt: str,
    ) -> None:
        buf = io.BytesIO()
        if fmt == "parquet":
            df.write_parquet(buf, compression="snappy")
        elif fmt == "csv":
            df.write_csv(buf)
        else:
            raise ValueError(f"Unsupported format: '{fmt}'.")
        buf.seek(0)
        try:
            self._bucket.put_object(path, buf)
        except Exception as e:
            raise RuntimeError(f"OSS write to '{path}' failed: {e}") from e

    def export(self) -> dict:
        return {
            "name": self.name,
            "type": "oss",
            "bucket": self.connection.bucket_name,
            "base_prefix": self._base_prefix,
            "format": self.setting.format,
            "connection": self.connection.export(),
        }
