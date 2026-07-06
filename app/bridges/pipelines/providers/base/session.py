from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from threading import RLock
from typing import Any

from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)
from app.common.setting.bridges import BaseProviderSetting


class BaseSession(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
    ABC,
):
    """
    会话管理基类。

    封装底层连接的创建、复用与过期刷新逻辑。内置 TTL 机制：连接超过
    ttl_interval 秒后, get_session() 会自动触发 refresh()。

    Attributes:
        setting:      提供商配置，由构造器直接传入
        name:         Provider 实例名称，来自 setting.name
        ttl_seconds:  会话存活秒数, None 表示永不过期
        ttl_margin:   刷新安全边界(秒), 在到期前提前刷新, None 表示无边距
        ttl_interval: 实际有效秒数(ttl_seconds - ttl_margin), None 表示永不过期
        active_at:    当前会话最近激活时间

    Example:
        >>> class MySession(BaseSession):
        ...     def _create_session(self):
        ...         return create_connection()
        >>> session = MySession(setting=GlobalSetting.bridges.providers["my"])
        >>> conn = session.get_session()  # 自动 connect, 过期后自动 refresh

    """

    def __init__(
        self,
        setting: BaseProviderSetting,
    ) -> None:
        super().__init__()
        self.setting: BaseProviderSetting = setting
        self.name: str = setting.name
        self._ttl_seconds: int | None = self._resolve_ttl_seconds()
        self._ttl_margin: int | None = self._resolve_ttl_margin()
        self._session: Any | None = None
        self._active_at: datetime | None = None
        self._lock = RLock()

    def _resolve_ttl_seconds(self) -> int | None:
        ttl_seconds: int | None = self.setting.ttl_seconds
        if ttl_seconds is None:
            return ttl_seconds
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        return ttl_seconds

    def _resolve_ttl_margin(self) -> int | None:
        ttl_margin: int | None = self.setting.ttl_margin
        if ttl_margin is None:
            return None
        if ttl_margin < 0:
            raise ValueError("ttl_margin must be >= 0")
        if self._ttl_seconds is not None and ttl_margin >= self._ttl_seconds:
            raise ValueError("ttl_margin must be < ttl_seconds")
        return ttl_margin

    @property
    def ttl_seconds(self) -> int | None:
        return self._ttl_seconds

    @property
    def ttl_margin(self) -> int | None:
        return self._ttl_margin

    @property
    def ttl_interval(self) -> int | None:
        if self._ttl_seconds is None:
            return None
        if self._ttl_margin is not None:
            margin = self._ttl_margin
        else:
            margin = 0
        return self._ttl_seconds - margin

    @property
    def active_at(self) -> datetime | None:
        return self._active_at

    def is_ready(self) -> bool:
        session_ready = self._session is not None
        active_ready = self._active_at is not None
        return session_ready and active_ready

    def is_expired(self) -> bool:
        if not self.is_ready():
            return True
        if self.ttl_interval is None:
            return False
        delta = timedelta(seconds=self.ttl_interval)
        expire_at = self._active_at + delta
        current_dt = self._get_current_datetime()
        return current_dt >= expire_at

    @abstractmethod
    def _create_session(self) -> Any:
        raise NotImplementedError

    def _close_session(
        self,
        session: Any,
    ) -> None:
        # Optional for subclasses
        pass

    def connect(self) -> Any:
        with self._lock:
            self._session = self._create_session()
            self._active_at = self._get_current_datetime()
            self.info("connect: OK.")
            return self._session

    def close(self) -> None:
        with self._lock:
            if self._session is not None:
                try:
                    self._close_session(self._session)
                    self.info("close: OK.")
                except Exception as e:
                    self.warning(f"close: failed at {str(e)}")
                finally:
                    self._session = None
                    self._active_at = None

    def refresh(self) -> Any:
        with self._lock:
            prev_session = self._session
            curr_session = self._create_session()
            self._session = curr_session
            self._active_at = self._get_current_datetime()
            if prev_session is not None:
                try:
                    self._close_session(prev_session)
                except Exception as e:
                    self.warning(f"refresh: failed at {str(e)}")
            self.info("refresh: OK.")
            return self._session

    def get_session(self) -> Any:
        with self._lock:
            try:
                if not self.is_ready():
                    return self.connect()
                if self.is_expired():
                    return self.refresh()
                return self._session
            except Exception as e:
                self.error(f"get_session: failed at {str(e)}")
                raise

    def export(self) -> dict[str, Any]:
        if self.active_at is not None:
            active_at_str = self.active_at.isoformat()
        else:
            active_at_str = None

        return {
            "ttl_seconds": self.ttl_seconds,
            "ttl_margin": self.ttl_margin,
            "ttl_interval": self.ttl_interval,
            "active_at": active_at_str,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
