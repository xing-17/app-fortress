from __future__ import annotations

import json
from abc import abstractmethod
from pathlib import Path
from typing import Any, ClassVar

import polars as pl
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.bridges.resources.accessory.coolant import Coolant
from app.bridges.resources.accessory.paginate import Paginate
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.sources.base.setting import (
    BaseSourceSetting,
    RetrySetting,
)
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)


class BaseSource(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    """
    数据源基类。

    定义从 YAML 配置加载的数据源的基础结构，提供缓存管理、重试机制、
    分页抓取等通用功能。子类只需实现 build_params 和 _fetch_all 方法。

    Attributes:
        _setting_class (ClassVar): 子类声明，对应的 Setting 类，供 from_yaml 使用
        setting (BaseSourceSetting): 数据源配置对象
        name (str): 数据源名称，来自 setting.name
        provider_type (str): Provider 类型，来自 setting.provider_type
        tags (dict): 数据源标签，来自 setting.tags
        coolant (Coolant): 请求速率限制实例
        paginate (Paginate): 分页管理实例

    Methods:
        from_yaml(path): 类方法，从 YAML 文件加载 setting 并构建实例
        run(provider, params): 主执行方法，包含缓存检查、数据获取、缓存写入
        build_params(params): 抽象方法，组装 API 调用参数（子类实现）
        _fetch_all(provider, params): 抽象方法，分页获取所有数据（子类实现）
        _call_with_retry(provider, method, params): 带重试逻辑的 API 调用
        _check_retriable(exc): 判断异常是否可重试
        export(): 导出数据源配置为字典
        describe(): 导出配置为格式化 JSON 字符串

    Example:
        >>> class MySource(BaseSource):
        ...     _setting_class = MySourceSetting
        ...
        ...     def build_params(self, params):
        ...         return params
        ...
        ...     def _fetch_all(self, provider, params):
        ...         return provider.call(self.setting.method, **params)
        >>>
        >>> source = MySource.from_yaml("items/my.yaml")
        >>> data = source.run(provider, {"date": "20240101"})

    """

    _setting_class: ClassVar[type[BaseSourceSetting]] = BaseSourceSetting

    @classmethod
    def from_yaml(
        cls,
        path: str | Path,
    ) -> "BaseSource":
        setting = cls._setting_class.from_yaml(path)
        return cls(setting=setting)

    def __init__(
        self,
        setting: BaseSourceSetting,
    ) -> None:
        self.setting = setting
        self.name = setting.name
        self.provider_type = setting.provider_type
        self.tags = setting.tags
        self.coolant = self._resolve_coolant()
        self.paginate = self._resolve_paginate()
        self._set_log_prefix(f"Source({self.name})")

    def _resolve_coolant(self) -> Coolant:
        return Coolant(
            interval=self.setting.coolant.interval,
        )

    def _resolve_paginate(self) -> Paginate:
        return Paginate(
            page_size=self.setting.paginate.page_size,
            max_pages=self.setting.paginate.max_pages,
        )

    def _resolve_partitions(
        self,
        params: dict[str, Any],
    ) -> list[str]:
        partitions = []
        for k, v in sorted(params.items()):
            partitions.append(f"{k}={v}")
        return partitions

    def run(
        self,
        provider: BaseProvider,
        params: dict[str, Any],
    ) -> pl.DataFrame:
        cache_partition = self._resolve_partitions(params)
        cache_key = self.name
        use_cache = provider.setting.use_cache
        cache = provider.cache

        # Cache hit
        if use_cache and cache.check(cache_key, cache_partition):
            data = cache.read(cache_key, cache_partition)
            if data is not None and not data.is_empty():
                return data

        # Cache miss: fetch
        data = self._fetch_all(
            provider=provider,
            params=self.build_params(params),
        )

        # Write cache if enabled
        if use_cache and not data.is_empty():
            cache.write(
                key=cache_key,
                data=data,
                partition=cache_partition,
            )

        return data

    def _call_with_retry(
        self,
        provider: BaseProvider,
        method: str,
        params: dict[str, Any],
    ) -> pl.DataFrame | None:
        # Retry setting
        r = self.setting.retry

        # 自定义 before_sleep 回调，使用我们的 LogPlugin
        def _log_retry(retry_state):
            attempt = retry_state.attempt_number
            outcome = retry_state.outcome
            if outcome and outcome.failed:
                exc = outcome.exception()
                self.warning(
                    f"Retry attempt {attempt} after error: {exc}",
                    context={"method": method},
                )

        # Wrap the provider call with tenacity
        @retry(
            retry=retry_if_exception(self._check_retriable),
            stop=stop_after_attempt((r.max_retries or 0) + 1),
            wait=wait_exponential(
                min=r.interval or 1.0,
                multiplier=r.backoff_rate or 1.0,
            ),
            before_sleep=_log_retry,
            reraise=True,
        )
        def _call() -> pl.DataFrame | None:
            return provider.call(
                method,
                **params,
            )

        # Call API with retry logic
        try:
            return _call()
        except Exception as e:
            if not self._check_retriable(e):
                self.warning(f"_call_with_retry: ignored [{e}]")
                return None
            raise

    def _check_retriable(
        self,
        exc: Exception,
    ) -> bool:
        retry_setting: RetrySetting = self.setting.retry
        patterns: list[str] = retry_setting.ignore_patterns
        if not patterns:
            return True
        else:
            msg = str(exc)
            is_patterned = any(p in msg for p in patterns)
            return not is_patterned

    @abstractmethod
    def build_params(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def _fetch_all(
        self,
        provider: BaseProvider,
        params: dict[str, Any],
    ) -> pl.DataFrame:
        raise NotImplementedError

    def transform(
        self,
        data: pl.DataFrame,
    ) -> pl.DataFrame:
        # Optional for subclasses to override for data transformation
        return data

    def export(self) -> dict:
        return {
            "setting": self.setting.export(),
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
