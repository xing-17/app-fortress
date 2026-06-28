from __future__ import annotations

from app.common.setting.base import BaseSetting


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

    target: str
    path: str = "./cache/centre/centre.duckdb"
    threads: int = 1
    extensions: list[str] = ["httpfs"]
    settings: dict = {}
