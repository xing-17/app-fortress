from __future__ import annotations

import json
from typing import ClassVar

from pydantic import Field

from app.common.context.base import BaseContext


class BridgesRequest(BaseContext):
    """
    Bridges 请求对象，包含请求的详细信息。

    Attributes:
        providers: 数据源提供商配置，例: dict[tushare: tushare_prod]
        sources_by_tags: 按标签分类的数据源，例: dict[region: us, type: stock]
        params: API运行参数，例: dict[start_date: 2023-01-01]
        destinations: 输出目标列表，例: [file, database]

    Methods:
        export(): 导出请求配置为字典
        describe(): 导出请求配置为 JSON 字符串

    Example:
        >>> request = BridgesRequest(
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

    def export(self) -> dict[str, any]:
        result = super().export()
        result.update(
            {
                "providers": self.providers,
                "sources_by_tags": self.sources_by_tags,
                "params": self.params,
                "destinations": self.destinations,
            }
        )
        return result

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
