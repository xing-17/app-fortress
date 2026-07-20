from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import ConfigDict, Field

from app.bridges.resources.destinations.base.destination import BaseDestination
from app.common.context.base import BaseContext

if TYPE_CHECKING:
    pass


class MigrateNodeContext(BaseContext):
    """
    Migrate 层最小执行单元上下文（不可变）。

    描述单次数据迁移任务所需的全部信息，作为 MigrateNode 的输入配置。
    包含源目标、目标存储、转换逻辑和执行参数的完整配置。

    层级关系：
        MigrateRequest → MigrateService → MigrateNode → MigrateNodeContext

    职责：
        - 封装单次数据迁移任务的完整配置
        - 关联 from_destination（源存储目标）和 to_destination（目标存储目标）
        - 指定源文件路径 glob 和目标文件路径 glob
        - 携带 DuckDB SQL 转换语句和执行选项
        - 配置 DuckDB 扩展和 COPY 选项

    Attributes:
        id (str): 自动生成的唯一标识，格式 mignctx_xxxxxxxxxxxx
        request_id (str): 所属迁移请求 ID
        source_name (str): 源数据源名称，用于标识迁移任务
        from_destination (BaseDestination): 源存储目标实例
        from_glob (str): 源文件路径 glob 模式（如 s3://bucket/prefix/**/*.parquet）
        to_destination (BaseDestination): 目标存储目标实例
        to_glob (str): 目标文件路径 glob 模式（如 s3://bucket/prefix/**/*.parquet）
        transform_sql (str | None): 可选的 DuckDB SQL 转换语句，<source> 作为占位符
        options (list[str]): DuckDB COPY TO 选项列表（如 ['OVERWRITE_OR_IGNORE true']）
        extensions (list[str]): DuckDB 扩展列表（如 ['httpfs']）
        created_at (datetime): 创建时间（继承自 BaseContext）
        category (str): 类别名称（继承自 BaseContext）

    Example:
        >>> context = MigrateNodeContext(
        ...     request_id="mig_abc123",
        ...     source_name="tushare_stock_capflow",
        ...     from_destination=oss_finconnect_dest,
        ...     from_glob="s3://bucket-src/finconnect/landing/tushare_stock_capflow/**/*.parquet",
        ...     to_destination=oss_fortress_dest,
        ...     to_glob="s3://bucket-tgt/fortress/bridges/source/tushare_stock_capflow/**/*.parquet",
        ...     transform_sql="SELECT * EXCLUDE(stock_code) FROM <source>",
        ... )
        >>> node = MigrateNode(context)
        >>> state = node.run()

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    id_prefix: ClassVar[str] = "mignctx"
    id_length: ClassVar[int] = 12

    request_id: str = Field(
        ...,
        description="所属 请求ID",
    )
    source_name: str = Field(
        ...,
        description="源数据源名称",
    )
    from_destination: BaseDestination = Field(
        ...,
        description="读取目标",
    )
    from_glob: str = Field(
        ...,
        description="源文件的 OSS 路径glob(如 s3://bucket/prefix/**/*.parquet)",
    )
    to_destination: BaseDestination = Field(
        ...,
        description="写出目标",
    )
    to_glob: str = Field(
        ...,
        description="目标文件的 OSS 路径glob(如 s3://bucket/prefix/**/*.parquet)",
    )
    transform_sql: str | None = Field(
        None,
        description="可选的 SQL 转换语句，用于在迁移过程中对数据进行转换",
    )
    options: list[str] = Field(
        default_factory=list,
        description="迁移选项列表，如 ['overwrite', 'validate']",
    )
    extensions: list[str] = Field(
        default_factory=list,
        description="迁移扩展列表，如 ['gzip', 'snappy']",
    )

    @property
    def identifier(self) -> str:
        return f"{self.source_name}::{self.id}"

    def export(self) -> dict[str, Any]:
        result = super().export()
        result.update(
            {
                "id": self.id,
                "request_id": self.request_id,
                "source_name": self.source_name,
                "from_destination": self.from_destination.name,
                "from_glob": self.from_glob,
                "to_destination": self.to_destination.name,
                "to_glob": self.to_glob,
                "transform_sql": self.transform_sql,
                "options": self.options,
                "extensions": self.extensions,
            }
        )
        return result
