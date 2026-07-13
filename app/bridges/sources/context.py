from __future__ import annotations

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.sources.base.source import BaseSource
from app.common.context.base import BaseContext


class SourceContext(BaseContext):
    """
    Source 层最小执行单元上下文（不可变）。

    描述单次原子抓取任务所需的全部信息，作为 SourceNode 的输入配置。
    包含数据提供商、数据源、目标存储和运行参数的完整配置。

    层级关系：
        BridgesRequest → PipeNode → SourceNode → SourceContext

    职责：
        - 封装单次数据抓取任务的完整配置
        - 关联 provider（数据提供商实例）
        - 关联 source（数据源定义，含方法、字段、分区规格）
        - 关联 destinations（写出目标列表）
        - 携带运行参数（由上层 Pipeline 填充，如时间范围）

    Attributes:
        id (str): 自动生成的唯一标识，格式 sctx_xxxxxxxxxxxx
        request_id (str): 所属请求 ID
        pipeline_id (str): 所属 Pipeline ID
        provider (BaseProvider): 数据提供商实例（如 TushareProvider）
        source (BaseSource): 数据源实例，包含方法、字段、分区、重试等配置
        destinations (list[BaseDestination]): 写出目标列表，至少包含一个目标
        params (dict[str, Any]): 本次运行参数，由上层填充，如 {"start_date": "2024-01-01"}
        created_at (datetime): 创建时间（继承自 BaseContext）
        category (str): 类别名称（继承自 BaseContext）

    Example:
        >>> context = SourceContext(
        ...     request_id="req_abc123",
        ...     pipeline_id="pipe_xyz456",
        ...     provider=tushare_provider,
        ...     source=daily_basic_source,
        ...     destinations=[postgres_dest, parquet_dest],
        ...     params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
        ... )
        >>> node = SourceNode(context)
        >>> state = node.run()

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    id_prefix: ClassVar[str] = "sctx"
    id_length: ClassVar[int] = 12

    request_id: str = Field(
        ...,
        description="所属 请求ID",
    )
    pipeline_id: str = Field(
        ...,
        description="所属 Pipeline ID",
    )
    provider: BaseProvider = Field(
        ...,
        description="数据提供商实例",
    )
    source: BaseSource = Field(
        ...,
        description="数据源实例",
    )
    destinations: list[BaseDestination] = Field(
        ...,
        min_length=1,
        description="写出目标列表",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="本次具体运行参数（由 Strategy 填充）",
    )
