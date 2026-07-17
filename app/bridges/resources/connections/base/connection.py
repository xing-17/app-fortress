from __future__ import annotations

import json
from abc import ABC, abstractmethod
from threading import RLock
from typing import Any

from app.bridges.resources.secret.duckdb import SecretDuckdb
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)
from app.common.setting.connections import BaseConnectionSetting


class BaseConnection(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
    ABC,
):
    """
    Connection 基类, 封装底层连接实例的创建与维护

    Attributes:
        setting: 连接配置(来自 connections.yml)
        name: 连接标识名
        type: 连接类型
        _connection: 底层连接实例
        _lock: 线程锁，确保连接创建的线程安全

    Methods:
        _create_connection(): [必须] 创建底层连接实例
        ping(): [必须] 检查连接是否可用
        get_duckdb_secret(): [可选] 获取连接对应的 DuckDB Secret 对象
        get_connection(): 获取底层连接实例
        connect(): 创建底层连接实例
        close(): 关闭底层连接实例
        export(): 导出连接信息为字典
        describe(): 导出连接信息为 JSON 字符串

    Example:
        >>> @ConnectionFactory.register("oss")
        ... class OSSConnection(BaseConnection):
        ...     def _create_connection(self) -> oss2.Bucket:
        ...         return oss2.Bucket(...)
        ...     def ping(self) -> bool: ...
        >>> conn = OSSConnection(setting=oss_setting)
        >>> bucket = conn.get_connection()  # → oss2.Bucket

    """

    def __init__(
        self,
        setting: BaseConnectionSetting,
    ) -> None:
        super().__init__()
        self.setting: BaseConnectionSetting = setting
        self.name: str = setting.name
        self.type: str = setting.type
        self._connection: Any | None = None
        self._lock: RLock = RLock()
        self._set_log_prefix(f"BaseConnection({self.name})")

    @property
    def is_connected(self) -> bool:
        return self._connection is not None

    @abstractmethod
    def _create_connection(self) -> Any:
        """
        [必须] 创建底层连接实例。

        Returns:
            Any: 底层连接实例（如 oss2.Bucket、duckdb.DuckDBPyConnection 等）

        """
        raise NotImplementedError

    @abstractmethod
    def ping(self) -> bool:
        """
        [必须] 检查连接是否可用。

        Returns:
            bool: True 表示连接可用，False 表示连接不可用
        """
        raise NotImplementedError

    @abstractmethod
    def get_duckdb_secret(self) -> SecretDuckdb | None:
        """
        [可选] 获取连接对应的 DuckDB Secret 对象。

        Returns:
            SecretDuckdb | None: DuckDB Secret 对象，如果不支持则返回 None

        """
        return None  # type: ignore

    def get_connection(self) -> Any:
        self.connect()
        return self._connection

    def connect(self) -> None:
        self.tick("connect")
        with self._lock:
            if self._connection is None:
                self._connection = self._create_connection()
                self.info("connect: OK.")
                seconds = self.tock("connect")
                self.debug(f"connect: duration {seconds:.3f}s.")

    def close(self) -> None:
        self.tick("close")
        with self._lock:
            self._connection = None
            self.info("close: OK.")
            seconds = self.tock("close")
            self.debug(f"close: duration {seconds:.3f}s.")

    def export(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "is_connected": self.is_connected,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
