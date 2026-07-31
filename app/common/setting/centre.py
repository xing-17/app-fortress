from __future__ import annotations

from pydantic import Field

from app.common.setting.base import BaseSetting
from app.common.setting.connections import BaseConnectionSetting


class CentreSetting(BaseSetting):
    """
    中心DBT配置。

    Attributes:
        target: 目标配置
        path: 配置路径，默认为 "./cache/centre/centre.duckdb"
        threads: 线程数，默认为 1
        extensions: 扩展列表，默认为 ["httpfs"]
        settings: 其他设置，默认为空字典

    Examples:
        >>> centre_setting = CentreSetting(target="my_target")
        >>> print(centre_setting.path)  # 输出: ./cache/centre/centre.duckdb
        >>> print(centre_setting.threads)  # 输出: 1
        >>> print(centre_setting.extensions)  # 输出: ['httpfs']
        >>> print(centre_setting.settings)  # 输出: {}

    """

    connection: str = Field(
        ...,
        description="连接名，对应 connections.yml 中的 key",
    )
    base_prefix: str = Field(
        "fortress/centre/",
        description="中心配置的基础前缀路径，默认为 fortress/centre/",
    )
    path: str = Field(
        ".cache/centre/centre.duckdb",
        description="配置路径，默认为 ./cache/centre/centre.duckdb",
    )
    max_threads: int = Field(
        1,
        description="dbt 并发线程数(1=串行, N>1=并发执行)",
        ge=1,
    )
    max_queue_size: int = Field(
        100,
        description="请求队列最大长度, 超过则拒绝新请求",
        ge=1,
    )
    registry_path: str = ".cache/centre/registry/centre.json"
    max_registry_items: int | None = Field(
        default=None,
        description="最大注册表条目数，超过此数量时将触发清理",
    )
    extensions: list[str] = ["httpfs", "s3"]
    settings: dict = Field(default_factory=dict)
