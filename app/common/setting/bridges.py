from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.common.setting.base import BaseSetting


class BridgesDestinationSetting(BaseSetting):
    """
    Destination 配置项(bridges.yml destinations[])。

    Attributes:
        name:        Destination 标识名
        connection:  引用 connections.yml 中的连接名
        base_prefix: OSS 路径前缀(如 fortress/data/tushare)
        format:      写出格式, 当前仅支持 parquet

    Examples:
        >>> dest = BridgesDestinationSetting(
        ...     name="oss_prod_tushare",
        ...     connection="oss_prod",
        ...     base_prefix="fortress/data/tushare",
        ... )
        >>> dest.connection  # "oss_prod"

    """

    name: str = Field(
        ...,
        description="Destination 标识名",
    )
    connection: str = Field(
        ...,
        description="引用 connections.yml 中的连接名",
    )
    base_prefix: str = Field(
        ...,
        description="写出路径前缀",
    )
    format: Literal["parquet", "csv"] = Field(
        "parquet",
        description="写出格式",
    )


class BaseProviderSetting(BaseSetting):
    """
    数据提供商基础配置。

    Attributes:
        name: 提供商标识名
        type: 提供商类型
        region: 服务地区, 默认 "cn"
        use_cache: 是否启用缓存, 默认 True
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

    name: str = Field(
        ...,
        description="提供商标识名",
    )
    type: str = Field(
        ...,
        description="提供商类型",
    )
    region: str = Field(
        "cn",
        description="服务地区",
    )
    use_cache: bool = Field(
        True,
        description="是否启用缓存",
    )
    ttl_seconds: int | None = Field(
        None,
        description="缓存 TTL(秒)",
    )
    ttl_margin: int | None = Field(
        None,
        description="缓存 TTL 边际(秒)",
    )
    jitter_min_seconds: float | None = Field(
        None,
        description="请求抖动最小值(秒)",
    )
    jitter_max_seconds: float | None = Field(
        None,
        description="请求抖动最大值(秒)",
    )
    max_threads: int = Field(
        1,
        description="Provider 内并发线程数(1=串行, N>1=并发执行 SourceContext)",
        ge=1,
    )
    cache: BridgesCacheSetting | None = Field(
        None,
        description="缓存配置, 若未指定则使用全局 Bridges.cache 配置",
    )


class TushareProviderSetting(BaseProviderSetting):
    """
    Tushare 数据提供商配置。

    Attributes:
        type:                 固定为 "tushare", 用于类型分发
        region:               服务地区, 默认 "cn"
        secret:               Tushare API Token, 可选(dev 实例可不配置)
        ttl_seconds:          缓存 TTL(秒), 默认 1800
        ttl_margin:           缓存 TTL 边际(秒), 默认 60
        use_cache:            是否启用缓存, 默认 True
        jitter_min_seconds:   请求抖动最小值(秒), 默认 1.0
        jitter_max_seconds:   请求抖动最大值(秒), 默认 1.5

    Examples:
        >>> ts = TushareProviderSetting(
        ...     secret="your_token_here",
        ... )
        >>> print(ts.ttl_seconds) # 1800

    """

    type: Literal["tushare"] = "tushare"
    secret: str | None = Field(None, description="Tushare API Token")
    timeout: int | None = Field(30, description="请求超时时间(秒)")
    ttl_seconds: int | None = 1800
    ttl_margin: int | None = 60
    use_cache: bool = True
    jitter_min_seconds: float | None = 0.2
    jitter_max_seconds: float | None = 1.0

    def export(self) -> dict:
        result = super().export()
        result["secret"] = (self.secret[:4] + "***") if self.secret else None
        return result


ProviderSetting = Annotated[
    Union[TushareProviderSetting,],
    Field(discriminator="type"),
]


class BridgesCoreSetting(BaseSetting):
    """
    Bridges 执行配置(bridges.yml bridges 节)。

    Attributes:
        max_threads: 跨 provider 并发线程数。
                     1 = 串行执行(默认); N > 1 = 同时执行 N 个 PipelineContext。
        max_queue_size: 请求队列最大长度, 超过则拒绝新请求
        registry_path: Registry 文件路径, 需在 Registry 连接中可写

    Examples:
        >>> exec_setting = BridgesExecutionSetting(max_threads=4)
        >>> print(exec_setting.max_threads)  # 4
    """

    max_threads: int = Field(
        1,
        description="跨 provider 并发线程数(1=串行, N>1=并发执行 PipelineContext)",
        ge=1,
    )
    max_queue_size: int = Field(
        100,
        description="请求队列最大长度, 超过则拒绝新请求",
        ge=1,
    )
    registry_path: str = Field(
        ".cache/bridges/registry.json",
        description="Registry 文件路径, 需在 Registry 连接中可写",
    )
    max_registry_items: int | None = Field(
        None,
        description="Registry 最大记录数, 超过则删除最旧记录",
    )


class BridgesMigrateSetting(BaseSetting):
    """
    Bridges Migrate 执行配置(bridges.yml bridges.migrate 节)。

    Attributes:
        max_threads: 跨 provider 并发线程数。
                     1 = 串行执行(默认); N > 1 = 同时执行 N 个 PipelineContext。
        max_queue_size: 请求队列最大长度, 超过则拒绝新请求
        registry_path: Registry 文件路径, 需在 Registry 连接中可写

    Examples:
        >>> migrate_setting = BridgesMigrateSetting(max_threads=2)
        >>> print(migrate_setting.max_threads)  # 2
    """

    max_threads: int = Field(
        1,
        description="服务端request并发线程数(1=串行, N>1=并发执行)",
        ge=1,
    )
    max_queue_size: int = Field(
        100,
        description="请求队列最大长度, 超过则拒绝新请求",
        ge=1,
    )
    memory_limit: str = Field(
        "4GB",
        description="内存限制",
    )
    max_workers: int = Field(
        2,
        description="DuckDB 最大并发线程数",
    )
    options: list[str] = Field(
        default_factory=list,
        description="迁移选项",
    )
    extensions: list[str] = Field(
        default_factory=list,
        description="DuckDB 扩展列表",
    )
    temp_directory: str = Field(
        ".cache/bridges/temp/migrate",
        description="临时目录",
    )
    registry_path: str = Field(
        ".cache/bridges/registry/migrate.json",
        description="Registry 文件路径, 需在 Registry 连接中可写",
    )
    max_registry_items: int | None = Field(
        None,
        description="Registry 最大记录数, 超过则删除最旧记录",
    )


class BridgesCacheSetting(BaseSetting):
    """
    缓存配置。

    Attributes:
        name: 缓存名称, 默认 "cache"
        path: 缓存文件路径, 默认 ".cache/bridges/cache.duckdb"
        ttl_hours: 缓存过期时间(小时), 默认 48
        ttl_table: TTL 元数据表名, 默认 "__system_ttl"
        hash_length: 哈希长度, 默认 16

    Examples:
        >>> cache_setting = BridgesCacheSetting()
        >>> print(cache_setting.path)  # 输出: .cache/bridges/cache.duckdb
        >>> print(cache_setting.ttl_hours)  # 输出: 48
    """

    name: str = "cache"
    path: str = ".cache/bridges/cache.duckdb"
    ttl_hours: int | None = 48
    ttl_table: str = "__system_ttl"
    hash_length: int = 16


class BridgesSetting(BaseSetting):
    """
    数据提供商配置集合。

    Attributes:
        providers: 提供商配置字典, 键为提供商名称, 值为具体的提供商配置

    Methods:
        get_provider: 根据提供商名称获取对应的提供商配置

    Examples:
        >>> bridges = BridgesSetting.from_yaml("setting/bridges.yml")
        >>> ts = bridges.get_provider("tushare")
        >>> print(ts.secret)

    """

    bridges: BridgesCoreSetting = Field(
        default_factory=BridgesCoreSetting,
        description="Bridges Core 执行配置",
    )
    migrate: BridgesMigrateSetting = Field(
        default_factory=BridgesMigrateSetting,
        description="Bridges Migrate 执行配置",
    )
    providers: dict[str, ProviderSetting]
    destinations: list[BridgesDestinationSetting] = Field(
        default_factory=list,
        description="写出目标列表",
    )
    source_paths: list[str] = Field(
        default_factory=list,
        description="配置来源路径列表",
    )
    cache: BridgesCacheSetting = Field(
        default_factory=BridgesCacheSetting,
        description="缓存配置",
    )

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

    def get_destination(
        self,
        name: str | None = None,
    ) -> BridgesDestinationSetting:
        for dest in self.destinations:
            if dest.name == name:
                return dest
        raise KeyError(f"Destination not found: {name!r}")

    def export(self) -> dict:
        result = {}
        result["bridges"] = self.bridges.export()
        result["providers"] = {}
        for name, provider in self.providers.items():
            result["providers"][name] = provider.export()
        result["destinations"] = [d.export() for d in self.destinations]
        result["source_paths"] = self.source_paths
        result["cache"] = self.cache.export()
        return result
