from __future__ import annotations

import json
import threading

from app.bridges.resources.cache.cache import BridgesCache, ModuleBridgesCache
from app.bridges.resources.connections.base.connection import BaseConnection
from app.bridges.resources.connections.base.factory import ConnectionFactory
from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.destinations.base.factory import DestinationFactory
from app.bridges.resources.providers.base.factory import ProviderFactory
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.sources.base.factory import SourceFactory
from app.bridges.resources.sources.base.source import BaseSource
from app.common.core.setting import GlobalSetting
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)
from app.common.setting.bridges import BridgesSetting


class BridgesWarehouse(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
):
    def __init__(self):
        super().__init__()
        self.setting: BridgesSetting = GlobalSetting.bridges
        self.cache: BridgesCache = ModuleBridgesCache

        self._provider_factory = self._resolve_provider_factory()
        self._connection_factory = self._resolve_connection_factory()
        self._destination_factory = self._resolve_destination_factory()
        self._source_factory = self._resolve_source_factory()

        self._providers: dict[str, BaseProvider] = {}
        self._connections: dict[str, BaseConnection] = {}
        self._destinations: dict[str, BaseDestination] = {}
        self._sources: dict[str, BaseSource] = {}

        self._lock = threading.Lock()
        self.load()

    def _resolve_provider_factory(self) -> ProviderFactory:
        return ProviderFactory()

    def _resolve_connection_factory(self) -> ConnectionFactory:
        return ConnectionFactory()

    def _resolve_destination_factory(self) -> DestinationFactory:
        return DestinationFactory()

    def _resolve_source_factory(self) -> SourceFactory:
        return SourceFactory()

    def load_providers(self) -> dict[str, BaseProvider]:
        return self._provider_factory.bootstrap()

    def load_connections(self) -> dict[str, BaseConnection]:
        return self._connection_factory.bootstrap()

    def load_destinations(self) -> dict[str, BaseDestination]:
        return self._destination_factory.bootstrap(self._connections)

    def load_sources(self) -> dict[str, BaseSource]:
        return self._source_factory.bootstrap()

    def load(self):
        with self._lock:
            self._providers: dict[str, BaseProvider] = self.load_providers()
            self._connections: dict[str, BaseConnection] = self.load_connections()
            self._destinations: dict[str, BaseDestination] = self.load_destinations()
            self._sources: dict[str, BaseSource] = self.load_sources()

    def refresh(self):
        self.load()
        self.cache.refresh()

    # --------------- Providers Access Methods ---------------

    def get_provider(
        self,
        name: str,
    ) -> BaseProvider:
        with self._lock:
            if name not in self._providers:
                raise ValueError(f"Provider '{name}' not found.")
            return self._providers.get(name)

    # resources.py
    def get_first_provider_by_type(
        self,
        type: str,
    ) -> BaseProvider:
        with self._lock:
            for provider in self._providers.values():
                if provider.type == type:
                    return provider
            raise ValueError(f"No provider found for type '{type}'.")

    # --------------- Destinations Access Methods ---------------

    def get_destination(
        self,
        name: str,
    ) -> BaseDestination:
        with self._lock:
            if name not in self._destinations:
                raise ValueError(f"Destination '{name}' not found.")
            return self._destinations.get(name)

    def list_destinations(
        self,
    ) -> list[BaseDestination]:
        with self._lock:
            return list(self._destinations.values())

    # --------------- Sources Access Methods ---------------

    def get_source(
        self,
        name: str,
    ) -> BaseSource:
        with self._lock:
            if name not in self._sources:
                raise ValueError(f"Source '{name}' not found.")
            return self._sources.get(name)

    def get_sources_by_tags(
        self,
        tags: dict[str, str],
    ) -> list[BaseSource]:
        with self._lock:
            result = []
            for source in self._sources.values():
                if all(source.tags.get(k) == v for k, v in tags.items()):
                    result.append(source)
            return result

    # --------------- Connections Access Methods ---------------

    def get_connection(
        self,
        name: str,
    ) -> BaseConnection:
        with self._lock:
            if name not in self._connections:
                raise ValueError(f"Connection '{name}' not found.")
            return self._connections.get(name)

    # --------------- Export Methods ---------------

    def _export_providers(self) -> dict:
        with self._lock:
            result = {}
            for name, provider in self._providers.items():
                result[name] = provider.export()
            return result

    def _export_connections(self) -> dict:
        with self._lock:
            result = {}
            for name, connection in self._connections.items():
                result[name] = connection.export()
            return result

    def _export_destinations(self) -> dict:
        with self._lock:
            result = {}
            for name, destination in self._destinations.items():
                result[name] = destination.export()
            return result

    def _export_sources(self) -> dict:
        with self._lock:
            result = {}
            for name, source in self._sources.items():
                result[name] = source.export()
            return result

    def export(self) -> dict:
        return {
            "providers": self._export_providers(),
            "connections": self._export_connections(),
            "destinations": self._export_destinations(),
            "sources": self._export_sources(),
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )


# ── 全局单例 ──────────────────────────────────────────────────────────────────────────────
# 在模块加载时即创建全局单例，供全局访问和使用
# 通过调用 `ModuleBridgesWarehouse.refresh()` 可在运行时刷新配置
ModuleBridgesWarehouse: BridgesWarehouse = BridgesWarehouse()
