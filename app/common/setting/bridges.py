from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.common.setting.base import BaseSetting


class BaseProviderSetting(BaseSetting):
    """
    数据提供商基础配置。

    Attributes:
        name: 提供商标识名
        type: 提供商类型
        region: 服务地区，默认 "cn"
        use_cache: 是否启用缓存，默认 True
        ttl_seconds: 缓存 TTL(秒)
        ttl_margin: 缓存 TTL 边际(秒)
        jitter_min_seconds: 请求抖动最小值(秒)
        jitter_max_seconds: 请求抖动最大值(秒)

    Examples:
        >>> setting = BaseProviderSetting(
        ...     name="example_provider",
        ...     type="example_type",
        ...     region="cn",
        ... )
        >>> print(setting.name)  # example_provider
        >>> print(setting.type)  # example_type
        >>> print(setting.region)  # cn
    """

    name: str = Field(..., description="提供商标识名")
    type: str = Field(..., description="提供商类型")
    region: str = Field("cn", description="服务地区")
    use_cache: bool = Field(True, description="是否启用缓存")
    ttl_seconds: int = Field(None, description="缓存 TTL(秒)")
    ttl_margin: int = Field(None, description="缓存 TTL 边际(秒)")
    jitter_min_seconds: float = Field(None, description="请求抖动最小值(秒)")
    jitter_max_seconds: float = Field(None, description="请求抖动最大值(秒)")

class TushareProviderSetting(BaseProviderSetting):
    """
    Tushare 数据提供商配置。

    Attributes:
        type:                 固定为 "tushare"，用于类型分发
        name:                 固定为 "tushare"
        region:               服务地区，默认 "cn"
        secret:               Tushare API Token
        ttl_seconds:          缓存 TTL(秒)，默认 1800
        ttl_margin:           缓存 TTL 边际(秒)，默认 60
        use_cache:            是否启用缓存，默认 True
        jitter_min_seconds:   请求抖动最小值(秒)，默认 1.0
        jitter_max_seconds:   请求抖动最大值(秒)，默认 1.5

    Examples:
        >>> ts = TushareProviderSetting(
        ...     secret="your_token_here",
        ... )
        >>> print(ts.ttl_seconds) # 1800

    """

    type: Literal["tushare"] = "tushare"
    name: str = "tushare"
    secret: str = Field(..., description="Tushare API Token")
    timeout: int = Field(30, description="请求超时时间(秒)")
    ttl_seconds: int = 1800
    ttl_margin: int = 60
    use_cache: bool = True
    jitter_min_seconds: float = 0.2
    jitter_max_seconds: float = 1.0

    def export(self) -> dict:
        result = super().export()
        result["secret"] = self.secret[:4] + "***"
        return result


ProviderSetting = Annotated[
    Union[TushareProviderSetting,],
    Field(discriminator="type"),
]


class BridgesCacheSetting(BaseSetting):
    """
    缓存配置。

    Attributes:
        name: 缓存名称，默认 "cache"
        path: 缓存文件路径，默认 ".cache/bridges/cache.duckdb"
        ttl_hours: 缓存过期时间(小时)，默认 48
        ttl_table: TTL 元数据表名，默认 "__system_ttl"
        hash_length: 哈希长度，默认 16

    Examples:
        >>> cache_setting = BridgesCacheSetting()
        >>> print(cache_setting.path)  # 输出: .cache/bridges/cache.duckdb
        >>> print(cache_setting.ttl_hours)  # 输出: 48
    """

    name: str = "cache"
    path: str = ".cache/bridges/cache.duckdb"
    ttl_hours: int = 48
    ttl_table: str = "__system_ttl"
    hash_length: int = 16


class BridgesSetting(BaseSetting):
    """
    数据提供商配置集合。

    Attributes:
        providers: 提供商配置字典，键为提供商名称，值为具体的提供商配置

    Methods:
        get_provider: 根据提供商名称获取对应的提供商配置

    Examples:
        >>> bridges = BridgesSetting.from_yaml("setting/bridges.yml")
        >>> ts = bridges.get_provider("tushare")
        >>> print(ts.secret)

    """

    providers: dict[str, ProviderSetting]
    source_paths: list[str] = Field(default_factory=list, description="配置来源路径列表")
    cache: BridgesCacheSetting = Field(default_factory=BridgesCacheSetting, description="缓存配置")

    def get_provider(
        self,
        name: str | None = None,
        type: str | None = None,
    ) -> ProviderSetting:
        if type is not None:
            for provider in self.providers.values():
                if provider.type == type:
                    return provider
            raise KeyError(f"Provider not found: type {type!r}.")
        if name is not None:
            try:
                return self.providers[name]
            except KeyError:
                raise KeyError(f"Provider not found: name {name!r}")
        raise ValueError("Either 'name' or 'type' must be provided.")

    def get_cache(self) -> BridgesCacheSetting:
        return self.cache

    def export(self) -> dict:
        result = {}
        result["providers"] = {}
        for name, provider in self.providers.items():
            result["providers"][name] = provider.export()
        result["source_paths"] = self.source_paths
        result["cache"] = self.cache.export()
        return result
