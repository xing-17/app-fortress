from __future__ import annotations

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.sources.base.source import BaseSource
from app.common.context.base import BaseContext


class PipelineContext(BaseContext):
    """
    Pipeline 层上下文。

    Attributes:
        request_id (str): 所属请求 ID
        provider: BaseProvider
        source: BaseSource
        destinations: list[BaseDestination]
        params: dict[str, Any] | None

    Methods:
        export() -> dict[str, Any]: 导出为字典
        describe() -> str: 导出为格式化 JSON 字符串

    Example:
        >>> context = PipelineContext(
        >>>     request_id="req_123",
        >>>     provider=provider_instance,
        >>>     source=source_instance,
        >>>     destinations=[dest1, dest2],
        >>>     params={"param1": "value1"},
        >>> )

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    id_prefix: ClassVar[str] = "pctx"
    id_length: ClassVar[int] = 10

    request_id: str = Field(
        ...,
        description="所属 请求ID",
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
        description="目标存储实例列表",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="本次具体运行参数（由上层 BridgesCluster 传入）",
    )

    def export(self) -> dict[str, Any]:
        result = super().export()
        result["request_id"] = self.request_id
        result["provider"] = self.provider.export()
        result["source"] = self.source.export()
        result["destinations"] = [d.export() for d in self.destinations]
        result["params"] = self.params
        return result
