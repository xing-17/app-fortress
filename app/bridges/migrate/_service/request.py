from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from app.common.context.base import BaseContext


class MigrateRequest(BaseContext):
    """
    数据迁移请求对象。

    Attributes:
        source_name:        迁移任务逻辑名称，用于日志标识
        from_destination:   源 Destination 名称
        from_glob:          源文件的 OSS 路径 glob(如 s3://bucket/prefix/**/*.parquet)
        to_destination:     目标 Destination 名称
        transform_sql:      DuckDB SQL 变换语句，<source> 为占位符，默认 SELECT * FROM <source>
        options:            DuckDB COPY TO 选项列表(如 ['OVERWRITE_OR_IGNORE true'])
        extensions:         DuckDB 扩展列表(如 ['httpfs'])

    Example:
        >>> # 基本迁移示例
        >>> request = MigrateRequest(
        ...     source_name='tushare_stock_capflow',
        ...     from_destination='oss_finconnect',
        ...     from_glob='finconnect/landing/tushare_stock_capflow/**/*.parquet',
        ...     to_destination='oss_fortress',
        ...     transform_sql='SELECT * EXCLUDE(stock_code) FROM <source>',
        ... )
        >>> # 带 DuckDB 选项的迁移
        >>> request = MigrateRequest(
        ...     source_name='tushare_stock_capflow',
        ...     from_destination='oss_prod',
        ...     from_glob='finconnect/landing/tushare_stock_capflow/**/*.parquet',
        ...     to_destination='oss_prod',
        ...     options=['FORMAT parquet', 'COMPRESSION snappy', 'OVERWRITE_OR_IGNORE true'],
        ...     extensions=['httpfs'],
        ... )
        >>> service = MigrateService()
        >>> request_id = service.submit(request)

    """

    id_prefix: ClassVar[str] = "mig"
    id_length: ClassVar[int] = 8

    source_name: str = Field(
        ...,
        description="迁移任务逻辑名称，用于日志标识",
    )
    from_destination: str = Field(
        ...,
        description="源 Destination 名称(从该 destination 所在 bucket 读取文件列表)",
    )
    from_glob: str = Field(
        ...,
        description="源文件的 OSS 路径glob(如 s3://bucket/prefix/**/*.parquet)",
    )
    to_destination: str = Field(
        ...,
        description="目标 Destination 名称(将文件写入该 destination 所在 bucket)",
    )
    transform_sql: str | None = Field(
        None,
        description=(
            "DuckDB SQL 变换语句。<source> 占位符会被替换为 "
            "read_parquet(glob_url)。默认 SELECT * FROM <source>。"
            "例: SELECT * EXCLUDE(stock_code) FROM <source>"
        ),
    )
    options: list[str] = Field(
        default_factory=list,
        description=(
            "DuckDB COPY TO 选项列表。例: ['FORMAT parquet', 'COMPRESSION snappy', 'OVERWRITE_OR_IGNORE true']"
        ),
    )
    extensions: list[str] = Field(
        default_factory=list,
        description=("DuckDB 扩展列表。例: ['httpfs']"),
    )

    def export(self) -> dict[str, str]:
        result = super().export()
        result["source_name"] = self.source_name
        result["from_destination"] = self.from_destination
        result["from_glob"] = self.from_glob
        result["to_destination"] = self.to_destination
        result["transform_sql"] = self.transform_sql
        result["options"] = self.options
        result["extensions"] = self.extensions
        return result
