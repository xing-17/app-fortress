from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from app.common.context.base import BaseContext


class BridgesMigrateRequest(BaseContext):
    """
    数据迁移请求对象。

    描述一次从 source_destination 到 target_destination 的文件批量迁移。
    迁移范围由 source_prefix 定义；默认保持原始 key 路径不变。

    Attributes:
        source_name:        迁移任务逻辑名称，同时作为自动推导 target 路径的子目录名
        from_destination:   源 Destination 名称
        from_prefix:        源文件的 OSS 路径前缀，支持 glob(如 **/*.parquet)
        to_destination:     目标 Destination 名称
        to_prefix:          目标路径前缀(可选)。为 None 时由 node 自动推导为
                            {tgt_dest.base_prefix}/source/{source_name}
        transform_sql:      DuckDB SQL 变换语句，<source> 为占位符，默认 SELECT * FROM <source>
        max_workers:        并发线程数(当前保留字段)，默认 8
        overwrite:          目标文件已存在时是否覆盖，默认 True

    Example:
        >>> # target_prefix 为 None：自动推导目标路径
        >>> request = BridgesMigrateRequest(
        ...     source_name='tushare_stock_capflow',
        ...     from_destination='oss_finconnect',
        ...     from_prefix='finconnect/landing/tushare_stock_capflow/**/*.parquet',
        ...     to_destination='oss_fortress',
        ...     transform_sql='SELECT * EXCLUDE(stock_code) FROM <source>',
        ... )
        >>> # to_prefix 显式指定(自定义命名)
        >>> request = BridgesMigrateRequest(
        ...     source_name='tushare_stock_capflow',
        ...     from_destination='oss_prod',
        ...     from_prefix='finconnect/landing/tushare_stock_capflow/**/*.parquet',
        ...     to_destination='oss_prod',
        ...     to_prefix='fortress/bridges/source/tushare_stock_capflow_migrated',
        ... )
        >>> service = BridgesMigrationService()
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
            "例：SELECT * EXCLUDE(stock_code) FROM <source>"
        ),
    )
    options: list[str] = Field(
        default_factory=list,
        description=(
            "DuckDB COPY TO 选项列表。例：['FORMAT parquet', 'COMPRESSION snappy', 'OVERWRITE_OR_IGNORE true']"
        ),
    )

    def export(self) -> dict[str, str]:
        result = super().export()
        result["source_name"] = self.source_name
        result["from_destination"] = self.from_destination
        result["from_glob"] = self.from_glob
        result["to_destination"] = self.to_destination
        result["transform_sql"] = self.transform_sql
        return result
