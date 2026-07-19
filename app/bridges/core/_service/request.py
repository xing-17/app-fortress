from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from app.common.context.base import BaseContext


class CoreRequest(BaseContext):
    """
    Core 数据抓取请求对象

    Attributes:
        providers: 数据源提供商配置，例: dict[tushare: tushare_prod]
        sources_by_tags: 按标签分类的数据源，例: dict[region: us, type: stock]
        params: API运行参数，例: dict[start_date: 2023-01-01]
        destinations: 输出目标列表，例: [file, database]

    Methods:
        export(): 导出请求配置为字典
        describe(): 导出请求配置为 JSON 字符串

    Example:
        >>> request = CoreRequest(
        ...     providers={"tushare": "tushare_prod"},
        ...     sources_by_tags={"region": "us", "type": "stock"},
        ...     params={"start_date": "2023-01-01"},
        ...     destinations=["file", "database"],
        ... )
        >>> request.export()
        >>> request.describe()

    """

    id_prefix: ClassVar[str] = "req"
    id_length: ClassVar[int] = 8

    providers: dict[str, str] = Field(
        default_factory=dict,
        description="数据源提供商配置, 例: dict[tushare: tushare_prod]",
    )
    sources_by_tags: dict[str, str] = Field(
        default_factory=dict,
        description="按标签分类的数据源, 例: dict[region: us, type: stock]",
    )
    params: dict[str, str] = Field(
        default_factory=dict,
        description="API运行参数, 例: dict[start_date: 2023-01-01]",
    )
    destinations: list[str] = Field(
        default_factory=list,
        description="输出目标列表, 例: [file, database]",
    )

    def export(self) -> dict[str, Any]:
        result = super().export()
        result["providers"] = self.providers
        result["sources_by_tags"] = self.sources_by_tags
        result["params"] = self.params
        result["destinations"] = self.destinations
        return result
