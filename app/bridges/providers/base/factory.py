from __future__ import annotations

from app.bridges.providers.base.provider import BaseProvider
from app.common.core.setting import GlobalSetting


class ProviderFactory:
    """
    Provider 注册工厂。

    基于类级注册表，通过 @ProviderFactory.register(type) 装饰器注册子类；
    bootstrap() 按 GlobalSetting.bridges.providers 批量创建所有 Provider。

    Methods:
        register:  装饰器，将 Provider 子类注册到全局注册表
        create:    按类型名创建并返回新的 Provider 实例
        bootstrap: 按全局配置批量创建所有 Provider，返回 {type: instance} 字典

    Example:
        >>> @ProviderFactory.register("tushare")
        ... class TushareProvider(BaseProvider): ...
        >>> providers = ProviderFactory.bootstrap()

    """

    _registry: dict[str, type[BaseProvider]] = {}

    @classmethod
    def register(
        cls,
        type: str,
    ):
        def decorator(klass: type[BaseProvider]):
            if type in cls._registry:
                raise ValueError(f"{type} Provider already registered.")
            cls._registry[type] = klass
            return klass

        return decorator

    @classmethod
    def create(
        cls,
        type: str,
    ) -> BaseProvider:
        klass = cls._registry.get(type)
        if klass is None:
            raise KeyError(f"Unknown {type} provider type.")
        return klass()

    @classmethod
    def bootstrap(cls) -> dict[str, BaseProvider]:
        result: dict[str, BaseProvider] = {}
        for type in GlobalSetting.bridges.providers:
            provider = cls.create(type)
            result[type] = provider
        return result
