from __future__ import annotations

from app.bridges.resources.providers.base.provider import BaseProvider
from app.common.core.setting import GlobalSetting
from app.common.setting.bridges import ProviderSetting


class ProviderFactory:
    """
    Provider 注册工厂。

    Methods:
        register(type):  装饰器，将 Provider 子类注册到全局注册表（key 为 type）
        create(name):    按实例名创建并返回新的 Provider 实例
        bootstrap():     按全局配置批量创建所有 Provider，返回 {name: instance} 字典

    Example:
        >>> @ProviderFactory.register("tushare")
        ... class TushareProvider(BaseProvider): ...
        >>> providers = ProviderFactory.bootstrap()

    """

    _registry: dict[str, type[BaseProvider]] = {}  # type -> class

    @classmethod
    def register(
        cls,
        type: str,
    ):
        def decorator(klass: type[BaseProvider]):
            if type in cls._registry:
                raise ValueError(f"Provider type '{type}' already registered.")
            cls._registry[type] = klass
            return klass

        return decorator

    @classmethod
    def create(
        cls,
        name: str,
    ) -> BaseProvider:
        providers_setting: dict[str, ProviderSetting] = GlobalSetting.bridges.providers
        if name not in providers_setting:
            raise KeyError(f"Provider name '{name}' not found.")
        provider_type = providers_setting[name].type
        klass = cls._registry.get(provider_type)
        if klass is None:
            raise KeyError(f"Unknown provider type: '{provider_type}'.")
        return klass(name=name)

    @classmethod
    def bootstrap(cls) -> dict[str, BaseProvider]:
        result: dict[str, BaseProvider] = {}
        providers_setting: dict[str, ProviderSetting] = GlobalSetting.bridges.providers
        for name in providers_setting.keys():
            result[name] = cls.create(name=name)  # name -> instance
        return result
