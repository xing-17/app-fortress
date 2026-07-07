from __future__ import annotations

from typing import Any

from pydantic import Field

from app.common.setting.base import BaseSetting


class CoolantSetting(BaseSetting):
    """
    冷却配置：每次请求后的固定等待时间。

    Attributes:
        interval: 冷却间隔（秒），None 表示不等待

    """

    interval: float | int | None = Field(
        None,
        description="冷却间隔(秒)",
    )


class PaginateSetting(BaseSetting):
    """
    分页配置：单次请求行数与最大翻页数。

    Attributes:
        page_size: 单次请求最大行数，None 使用默认值
        max_pages: 最多翻页次数，None 使用默认值

    """

    page_size: int | None = Field(
        None,
        description="分页大小",
    )
    max_pages: int | None = Field(
        None,
        description="最大分页数",
    )


class PartitionSetting(BaseSetting):
    """
    分区配置：写出路径中的分区键与列名。

    Attributes:
        prefix: 分区路径前缀，如 date → date=2024-01-02
        column: 分区列名，如 trade_date

    """

    prefix: str = Field(
        ...,
        description="分区路径前缀，如 date → date=2024-01-02",
    )
    column: str = Field(
        ...,
        description="分区列名，如 trade_date",
    )


class RetrySetting(BaseSetting):
    """
    重试配置：失败后的重试策略。

    Attributes:
        max_retries:  最大重试次数，None 使用默认值
        interval:     首次重试等待时间（秒），None 使用默认值
        backoff_rate: 退避倍率，1.0 = 固定间隔，2.0 = 指数退避

    """

    max_retries: int | None = Field(
        None,
        description="最大重试次数",
    )
    interval: float | None = Field(
        None,
        description="首次重试等待时间（秒）",
    )
    backoff_rate: float | None = Field(
        None,
        description="退避倍率, 1.0 = 固定间隔, 2.0 = 指数退避",
    )


class BaseSourceSetting(BaseSetting):
    """
    数据源配置基类。

    定义单个数据流的抓取规格，由 YAML 文件加载。
    描述「这张表怎么抓、怎么分区、用什么配置」。

    Attributes:
        name:          数据流唯一标识
        provider_type: provider 类型，如 tushare
        method:        provider API 方法名
        strategy:      数据流策略，如 by_date
        partition:     分区配置
        retry:         重试配置
        params:        可用运行时参数名列表（无值，由 PipeContext 填充）
        fields:        请求字段列表，空列表表示全部字段
        tags:          数据流标签列表，空列表表示无标签

    Methods:
        export(): 导出配置为字典

    Example:
        >>> setting = BaseSourceSetting.from_yaml("items/example.yaml")
        >>> setting.name
        >>> setting.method

    """

    name: str = Field(
        ...,
        description="数据流唯一标识",
    )
    provider_type: str = Field(
        ...,
        description="provider类型, 如 tushare",
    )
    method: str = Field(
        ...,
        description="provider 方法名",
    )
    strategy: str = Field(
        ...,
        description="数据流策略",
    )

    partition: PartitionSetting = Field(
        ...,
        description="分区设置",
    )
    retry: RetrySetting = Field(
        default_factory=RetrySetting,
        description="重试设置",
    )

    params: list[str] = Field(
        default_factory=list,
        description="可用运行时参数名",
    )
    fields: list[str] = Field(
        default_factory=list,
        description="请求字段列表",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="数据流标签列表",
    )

    def export(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider_type": self.provider_type,
            "method": self.method,
            "strategy": self.strategy,
            "partition": self.partition.export(),
            "retry": self.retry.export(),
            "params": self.params,
            "fields": self.fields,
            "tags": self.tags,
        }
