from __future__ import annotations

import json
from abc import ABC, abstractmethod
from threading import RLock
from typing import Any

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
    连接管理基类。

    封装底层连接实例的创建与维护。子类须实现 _create_connection() 和 ping()。
    连接实例在首次调用 get_connection() 时惰性创建，此后复用（长连接语义）。

    Attributes:
        setting: 连接配置（来自 connections.yml）
        name:    连接标识名
        type:    连接类型

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
        self._set_log_prefix(f"{self.__class__.__name__}({self.name})")

    @property
    def is_connected(self) -> bool:
        return self._connection is not None

    @abstractmethod
    def _create_connection(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def ping(self) -> bool:
        raise NotImplementedError

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
