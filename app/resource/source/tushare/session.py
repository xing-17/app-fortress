from __future__ import annotations

import threading
from typing import Any

import tushare
from pydantic import Field, PrivateAttr, model_validator

from app.internal.abstract.domain import IAbstractDomain
from app.internal.util.clock import IClock


class TushareSession(IAbstractDomain):
    """
    Tushare session management class.

    Attributes:
    ----------
        key (str):
            Tushare API token.
        ttl_hours (float):
            Connection time-to-live in hours. Must be greater than 0.
        connect_at (float | None):
            Timestamp when the session was last connected.
        expire_at (float | None):
            Timestamp when the session will expire.
        api (Any | None):
            Tushare API instance, if connected.

    Args:
    ----------
        key (str):
            Tushare API token.
        ttl_hours (float):
            Connection time-to-live in hours. Must be greater than 0.

    Methods:
    ----------
        is_expired() -> bool:
            Checks if the current session is expired.
        connect() -> Any:
            Establishes a connection to the Tushare API.

    """

    key: str = Field(
        ...,
        description="Tushare API token",
        min_length=1,
    )
    ttl_hours: float = Field(
        ...,
        description="Connection time-to-live in hours",
        gt=0,
    )
    _ttl_margin: float = PrivateAttr(default=60)
    _ttl_seconds: float | None = PrivateAttr(default=None)
    _connect_at: float | None = PrivateAttr(default=None)
    _expire_at: float | None = PrivateAttr(default=None)
    _api: Any | None = PrivateAttr(default=None)
    _lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)

    @model_validator(mode="after")
    def _derive_ttl_seconds(self) -> TushareSession:
        self._ttl_seconds = self.ttl_hours * 3600
        return self

    def is_expired(self) -> bool:
        if self._connect_at is None:
            return True
        if self._expire_at is None:
            return True
        _current: float = IClock.current_timestamp(timezone="UTC")
        return _current >= self._expire_at

    def connect(self) -> Any:
        with self._lock:
            self._api = tushare.pro_api(self.key)
            self._connect_at: float = IClock.current_timestamp(timezone="UTC")
            self._expire_at: float = self._connect_at + self._ttl_seconds - self._ttl_margin
            return self._api

    @property
    def api(self) -> Any:
        if self._api is None or self.is_expired():
            with self._lock:
                if self._api is None or self.is_expired():
                    self.connect()
        return self._api

    @property
    def connect_at(self) -> float | None:
        return self._connect_at

    @property
    def expire_at(self) -> float | None:
        return self._expire_at
