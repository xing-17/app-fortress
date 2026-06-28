from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from app.common.setting.base import BaseSetting


class BaseProviderSetting(BaseSetting):
    name: str = Field(..., description="提供商标识名")
    region: str = Field("cn", description="服务地区")


class TushareProviderSetting(BaseProviderSetting):
    """
    Tushare 数据提供商配置。

    Attributes:
        type:                 固定为 "tushare"，用于类型分发
        name:                 固定为 "tushare"
        region:               服务地区，默认 "cn"
        secret:               Tushare API Token
        ttl_seconds:          缓存 TTL（秒），默认 1800
        ttl_margin:           缓存 TTL 边际（秒），默认 60
        use_cache:            是否启用缓存，默认 True
        retry_max:            最大重试次数，默认 2
        retry_wait:           重试等待（秒），默认 60
        retry_rate:           重试速率，默认 1.0
        retry_skip_messages:  遇到这些错误消息时跳过重试
        coolant_interval:     冷却间隔（秒），默认 0
        jitter_min_seconds:   请求抖动最小值（秒），默认 1.0
        jitter_max_seconds:   请求抖动最大值（秒），默认 1.5

    Examples:
        >>> ts = TushareProviderSetting(
        ...     secret="your_token_here",
        ... )
        >>> print(ts.ttl_seconds) # 1800

    """

    type: Literal["tushare"] = "tushare"
    name: str = "tushare"
    secret: str = Field(..., description="Tushare API Token")
    ttl_seconds: int = 1800
    ttl_margin: int = 60
    use_cache: bool = True
    retry_max: int = 2
    retry_wait: int = 60
    retry_rate: float = 1.0
    retry_skip_messages: list[str] = []
    coolant_interval: int = 0
    jitter_min_seconds: float = 1.0
    jitter_max_seconds: float = 1.5


ProviderSetting = Annotated[
    Union[TushareProviderSetting,],
    Field(discriminator="type"),
]


class ProvidersSetting(BaseSetting):
    """
    数据提供商配置集合。

    Attributes:
        providers: 提供商配置字典，键为提供商名称，值为具体的提供商配置

    Examples:
        >>> providers = ProvidersSetting.from_yaml("setting/providers.yml")
        >>> ts = providers.get("tushare")
        >>> print(ts.secret)

    """

    providers: dict[str, ProviderSetting]

    def get(
        self,
        name: str,
    ) -> ProviderSetting:
        if name not in self.providers:
            raise KeyError(f"Provider not found: {name!r}")
        return self.providers[name]
