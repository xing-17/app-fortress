from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.clock import IClock
from app.internal.util.frn import IFrn
from app.resource.identity._common._identity import BaseIdentity
from app.resource.store._common._base import GovernedStoreResource
from app.setting._identity import AbstractIdentitySetting


class BaseTable(
    GovernedStoreResource,
    ABC,
):
    """
    Base class for store table resources, governed and derived from a parent database.

    A table can only be constructed via its parent database's `table()` method, which
    guarantees the table occupies exactly one path segment directly under the database
    (no nested names). Tables are the only resource in the store/database/table hierarchy
    that expose write capability; whether a `write` call behaves as an update or an append
    is entirely up to the business layer (determined by whether it reuses or invents `key`).

    Each key's stored value is wrapped in an envelope recording its write time and TTL:
    `{"data": <value>, "key": <key>, "written_at": <UTC timestamp>, "ttl": <seconds | None>}`.
    `written_at` is always a UTC POSIX timestamp. Expiry is never enforced automatically;
    callers must invoke `expire()` to actually purge expired keys.

    Args:
        name (str): Table name, must be a single path segment (no nested separators)
        storesystem (StoreSystem): Store system
        platform (Platform): Store platform
        identity (BaseIdentity | AbstractIdentitySetting | str | None): Table identity
        tags (dict[str, str]): Table tags
        ttl_hours (float | None): Default TTL, in hours, applied to keys written to this
            table; None (default) means written keys never expire

    Attributes:
        ttl_seconds (float | None): `ttl_hours` converted to seconds, or None.

    Methods:
        write(key: str, data: Any, strict: bool = False) -> None:
            Upsert a single key's value; content is not constrained.
        read(key: str | None = None, strict: bool = False) -> Any:
            Read a single key's value, or the entire content if key is None.
        delete(key: str, strict: bool = False) -> None:
            Delete a single key's value; raises if missing and strict is True.
        expire() -> None:
            Permanently remove all keys whose TTL has elapsed; must be called explicitly.

    """

    name: str = Field(
        ...,
        description="[Required] Table name, single path segment governed by the parent database",
    )
    storesystem: StoreSystem = Field(
        ...,
        description="[Required] Store system",
    )
    platform: Platform = Field(
        ...,
        description="[Required] Store platform",
    )
    identity: BaseIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Table identity",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="[Optional] Table tags",
    )
    ttl_hours: float | None = Field(
        default=None,
        description="[Optional] Default TTL in hours for keys written to this table; None means never expire",
    )

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "store",
                "database",
                "table",
                f"platform={self.platform}",
                f"storesystem={self.storesystem}",
                f"name={self.name}",
            ]
        )

    @property
    def ttl_seconds(self) -> float | None:
        if self.ttl_hours is None:
            return None
        return self.ttl_hours * 3600.0

    def _wrap(
        self,
        key: str,
        data: Any,
    ) -> dict[str, Any]:
        _now = IClock.current_timestamp(timezone="UTC")
        return {
            "data": data,
            "key": key,
            "written_at": _now,
            "ttl": self.ttl_seconds,
        }

    @staticmethod
    def _is_expired(
        envelope: dict[str, Any],
        now: float,
    ) -> bool:
        _ttl = envelope.get("ttl")
        if _ttl is None:
            return False
        _written_at = envelope.get("written_at", 0.0)
        return _written_at + _ttl <= now

    @abstractmethod
    def write(
        self,
        key: str,
        data: Any,
        strict: bool = False,
    ) -> None: ...

    @abstractmethod
    def read(
        self,
        key: str | None = None,
        strict: bool = False,
    ) -> Any: ...

    @abstractmethod
    def delete(
        self,
        key: str,
        strict: bool = False,
    ) -> None: ...

    @abstractmethod
    def expire(self) -> None: ...
