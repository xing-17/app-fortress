from __future__ import annotations

from app.common.setting.base import BaseSetting


class CacheSetting(BaseSetting):
    """
    缓存配置。

    Attributes:
        name: 缓存名称，默认 "cache"
        path: 缓存文件路径，默认 ".cache/bridges/cache.duckdb"
        ttl_hours: 缓存过期时间（小时），默认 48
        ttl_table: TTL 元数据表名，默认 "__system_ttl"
        hash_length: 哈希长度，默认 16

    Examples:
        >>> cache_setting = CacheSetting()
        >>> print(cache_setting.path)  # 输出: .cache/bridges/cache.duckdb
        >>> print(cache_setting.ttl_hours)  # 输出: 48
    """

    name: str = "cache"
    path: str = ".cache/bridges/cache.duckdb"
    ttl_hours: int = 48
    ttl_table: str = "__system_ttl"
    hash_length: int = 16
