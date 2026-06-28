from __future__ import annotations

from app.common.setting.base import BaseSetting


class CacheSetting(BaseSetting):
    """
    缓存配置。

    Attributes:
        name: 缓存名称，默认为 "cache"
        url: 缓存数据库连接 URL，默认为 "sqlite:///cache/system/cache.db"
        chunksize: 可选的缓存分块大小，默认为 None

    Examples:
        >>> cache_setting = CacheSetting()
        >>> print(cache_setting.name)  # 输出: cache
        >>> print(cache_setting.url)   # 输出: sqlite:///cache/system/cache.db
        >>> print(cache_setting.chunksize)  # 输出: None
    """

    name: str = "cache"
    url: str = "sqlite:///cache/system/cache.db"
    chunksize: int | None = None
