from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import Field

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.clock import IClock
from app.resource.identity._common._identity import BaseIdentity
from app.resource.store._common._base import GovernedStoreResource
from app.setting._identity import AbstractIdentitySetting


class BaseTable(
    GovernedStoreResource,
    ABC,
):
    """
    Base class for store table resources, governed and derived from parent.

    Each key's stored value is wrapped in an envelope recording its write time and TTL:
    `{"data": <value>, "key": <key>, "written_at": <UTC timestamp>, "ttl": <seconds | None>}`.
    `written_at` is always a UTC POSIX timestamp. Expiry is never enforced automatically;
    callers must invoke `expire()` to actually purge expired keys.

    Attributes:
    ----------
        storesystem (StoreSystem):
            Store system
        platform (Platform):
            Store platform
        ttl_seconds (float | None):
            `ttl_hours` converted to seconds, or None.
        frn (str):
            Table FRN, built from the table location so tables with equal names under different
            databases/stores stay distinct.

    Args:
    ----------
    name (str):
        Table name
    identity (BaseIdentity | AbstractIdentitySetting | str | None):
        Table identity
    tags (dict[str, str]):
        Table tags
    ttl_hours (float | None):
        Default TTL, in hours, applied to keys written to this table; must be > 0, None (default) means written keys never expire

    Methods:
    ----------
        write(key: str, data: Any, strict: bool = False) -> None:
            Upsert a single key's value; content is not constrained.
        read(key: str | None = None, strict: bool = False) -> Any:
            Read a single key's value, or the entire content if key is None.
        delete(key: str, strict: bool = False) -> None:
            Delete a single key's value; raises if missing and strict is True.
        expire() -> None:
            Permanently remove all keys whose TTL has elapsed; must be called explicitly.

    """

    # Enforced public class variables
    storesystem: ClassVar[StoreSystem]
    platform: ClassVar[Platform]

    # Enforced instance variables
    # [Inherited] tags: dict[str, str]
    name: str = Field(
        ...,
        description="[Required] Table name, single path segment governed by the parent database",
    )
    identity: BaseIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Table identity",
    )
    ttl_hours: float | None = Field(
        default=None,
        gt=0,
        description="[Optional] Default TTL in hours for keys written to this table, must be > 0; None means never expire",
    )

    @property
    @abstractmethod
    def frn(self) -> str: ...

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
