from __future__ import annotations

import json
from abc import ABC, abstractmethod
from threading import RLock
from typing import Any

from app.bridges.accessory.jitter import Jitter
from app.bridges.providers.base.session import BaseSession
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
    setting、_create_session、call、export 四个抽象成员。

    Attributes:
        type:      Provider 类型标识，来自 setting.type
        name:      Provider 名称，来自 setting.name
        region:    数据源所在区域，来自 setting.region
        use_cache: 是否启用缓存，来自 setting.use_cache
        jitter:    随机延迟对象，由 _create_jitter() 创建

    Example:
        >>> @ProviderFactory.register("my-type")
        ... class MyProvider(BaseProvider):
        ...     @property
        ...     def setting(self) -> BaseProviderSetting:
        ...         return GlobalSetting.bridges.providers["my-type"]
        ...     def _create_session(self) -> BaseSession:
        ...         return MySession(name=self.name, type=self.type, region=self.region)
        ...     def call(self, method: str, *args, **kwargs) -> Any:
        ...         return self.get_session().request(method, **kwargs)
        ...     def export(self) -> dict:
        ...         return {"name": self.name, "type": self.type}

    """

    def __init__(self) -> None:
        super().__init__()
        self.type: str = self.setting.type
        self.name: str = self.setting.name
        self.region: str = self.setting.region
        self.use_cache: bool = self.setting.use_cache
        self.jitter: Jitter = self._create_jitter()
        self._session: BaseSession = self._create_session()
        self._lock = RLock()

    @property
    @abstractmethod
    def setting(self) -> BaseProviderSetting:
        raise NotImplementedError("Subclasses must implement the 'setting' property.")

    def _create_jitter(self) -> Jitter:
        try:
            jitter = Jitter(
                min_seconds=getattr(
                    self.setting,
                    "jitter_min_seconds",
                    None,
                ),
                max_seconds=getattr(
                    self.setting,
                    "jitter_max_seconds",
                    None,
                ),
            )
            return jitter
        except Exception as e:
            self.warning(f"Failed to create Jitter: {e}")
            return Jitter()  # Return a default Jitter instance with no delay

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
        seconds = self.jitter.jit()
        self.debug(f"jit: {seconds} seconds OK.")

    @abstractmethod
    def export(self) -> dict[str, Any]:
        raise NotImplementedError("Subclasses must implement the 'export' method.")

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
