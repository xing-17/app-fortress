from __future__ import annotations

from app.bridges.resources.connections.base.connection import BaseConnection
from app.common.core.setting import GlobalSetting
from app.common.setting.connections import (
    BaseConnectionSetting,
    ConnectionsSetting,
)


class ConnectionFactory:
    """
    Connection 注册工厂。

    Methods:
        register(type): 装饰器，注册 Connection 子类
        create(name):   按名称创建单个 Connection 实例
        bootstrap():    按 bridges.yml connections 批量创建所有实例

    Example:
        >>> @ConnectionFactory.register("oss")
        ... class OSSConnection(BaseConnection): ...
        >>> connections = ConnectionFactory.bootstrap()

    """

    _registry: dict[str, type[BaseConnection]] = {}  # type → class

    @classmethod
    def register(
        cls,
        type: str,
    ):
        def decorator(klass: type[BaseConnection]):
            if type in cls._registry:
                raise ValueError(f"Connection type '{type}' already registered.")
            cls._registry[type] = klass
            return klass

        return decorator

    @classmethod
    def create(
        cls,
        name: str,
    ) -> BaseConnection:
        settings: ConnectionsSetting = GlobalSetting.connections
        setting: BaseConnectionSetting = settings.get(name)
        conn_type = setting.type
        klass = cls._registry.get(conn_type)
        if klass is None:
            raise KeyError(f"Unknown connection type '{conn_type}'.")
        return klass(setting=setting)

    @classmethod
    def bootstrap(cls) -> dict[str, BaseConnection]:
        result: dict[str, BaseConnection] = {}
        settings: ConnectionsSetting = GlobalSetting.connections
        for name in settings.connections.keys():
            result[name] = cls.create(name=name)
        return result
