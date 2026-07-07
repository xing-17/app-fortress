from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from app.bridges.resources.accessory.jitter import Jitter
from app.bridges.resources.cache.cache import (
    BridgesCache,
    ModuleBridgesCache,
)
from app.bridges.resources.providers.base.session import BaseSession
from app.common.core.setting import GlobalSetting
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)
from app.common.setting.bridges import BaseProviderSetting


class BaseProvider(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
    ABC,
):
    """
    数据提供者基类。

    定义 bridge 层数据源的通用接口与生命周期管理。子类须实现
    _create_session、call、export 三个抽象成员。

    Attributes:
        setting:   提供商配置，由 name 从 GlobalSetting 解析
        name:      Provider 实例名称，来自 setting.name
        type:      Provider 类型标识，来自 setting.type
        region:    数据源所在区域，来自 setting.region
        use_cache: 是否启用缓存，来自 setting.use_cache
        jitter:    随机延迟对象

    Example:
        >>> @ProviderFactory.register("my-type")
        ... class MyProvider(BaseProvider):
        ...     def _create_session(self) -> BaseSession:
        ...         return MySession(setting=self.setting)
        ...     def call(self, method: str, *args, **kwargs) -> Any:
        ...         return self.get_session().request(method, **kwargs)
        ...     def export(self) -> dict:
        ...         return {"name": self.name, "type": self.type}
        >>> provider = MyProvider(name="my-instance")

    """

    def __init__(
        self,
        name: str,
    ) -> None:
        super().__init__()
        self.setting: BaseProviderSetting = self._resolve_setting(name)
        self.name: str = self.setting.name
        self.type: str = self.setting.type
        self.region: str = self.setting.region
        self.cache: BridgesCache = ModuleBridgesCache
        self.jitter: Jitter = Jitter(
            min_seconds=self.setting.jitter_min_seconds,
            max_seconds=self.setting.jitter_max_seconds,
        )
        self._session: BaseSession = self._create_session()

    def _resolve_setting(
        self,
        name: str,
    ) -> BaseProviderSetting:
        providers_setting = GlobalSetting.bridges.providers
        if name not in providers_setting:
            raise KeyError(f"Provider '{name}' not found.")
        return providers_setting[name]

    @property
    def use_cache(self) -> bool:
        return self.setting.use_cache

    @abstractmethod
    def _create_session(self) -> BaseSession:
        raise NotImplementedError("Subclasses must implement the '_create_session' method.")

    def get_session(self) -> Any:
        return self._session.get_session()

    @abstractmethod
    def call(
        self,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        raise NotImplementedError("Subclasses must implement the 'call' method.")

    def jit(self) -> None:
        self.jitter.jit()

    @abstractmethod
    def export(self) -> dict[str, Any]:
        raise NotImplementedError("Subclasses must implement the 'export' method.")

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
