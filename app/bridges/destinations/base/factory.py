from __future__ import annotations

from app.bridges.connections.base.connection import BaseConnection
from app.bridges.destinations.base.destination import BaseDestination
from app.common.core.setting import GlobalSetting


class DestinationFactory:
    """
    Destination 注册工厂。

    Methods:
        register(type): 装饰器，注册 Destination 子类
        create(name):   按名称创建单个 Destination 实例
        bootstrap():    按 bridges.yml destinations 批量创建所有实例

    Example:
        >>> @DestinationFactory.register("oss")
        ... class OSSDestination(BaseDestination): ...
        >>> destinations = DestinationFactory.bootstrap(connections=connections)

    """

    _registry: dict[str, type[BaseDestination]] = {}  # type → class

    @classmethod
    def register(
        cls,
        type: str,
    ):
        def decorator(klass: type[BaseDestination]):
            if type in cls._registry:
                raise ValueError(f"Destination type '{type}' already registered.")
            cls._registry[type] = klass
            return klass

        return decorator

    @classmethod
    def create(
        cls,
        name: str,
        conn: BaseConnection,
    ) -> BaseDestination:
        conn_type: str = conn.type
        klass: type[BaseDestination] = cls._registry.get(conn_type)
        if klass is None:
            raise KeyError(f"Unknown destination type '{conn_type}'.")
        return klass(name=name, connection=conn)

    @classmethod
    def bootstrap(
        cls,
        connections: dict[str, BaseConnection],  # 从 cluster 注入
    ) -> dict[str, BaseDestination]:
        result: dict[str, BaseDestination] = {}
        for dest_setting in GlobalSetting.bridges.destinations:
            conn_name = dest_setting.connection
            if conn_name not in connections:
                raise KeyError(f"Connection '{conn_name}' not found.")
            conn: BaseConnection = connections[conn_name]
            dest_name = dest_setting.name
            result[dest_name] = cls.create(
                name=dest_name,
                conn=conn,
            )
        return result
