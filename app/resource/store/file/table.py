from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, ClassVar

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.clock import IClock
from app.internal.util.path import IPath
from app.resource._client.local.client import LocalObjectClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.local import LocalIdentity
from app.resource.store._common._table import BaseTable


class FileStoreTable(BaseTable):
    """
    File store table backed by a single JSON file.

    Attributes:
    ----------
        storesystem (StoreSystem):
            Store system type, fixed as FILE.
        platform (Platform):
            Store platform type, fixed as LOCAL.

    Args:
    ----------
        name (str):
            Table name, single path segment
        ttl_hours (float | None):
            Default TTL in hours for keys written to this table
        path (Path):
            Table file path, derived from the parent database path and name
        identity (LocalIdentity):
            Local identity associated with the table
        tags (dict[str, str]):
            Table tags

    Methods:
    ----------
        write(key: str, data: Any, strict: bool = False) -> None:
            Upsert data for key, wrapped in a {data, key, written_at, ttl} envelope.
        read(key: str | None = None, strict: bool = False) -> Any:
            Read the unwrapped data for key, or all unwrapped data if key is None.
        delete(key: str, strict: bool = False) -> None:
            Delete a key's value; raises KeyError if missing and strict is True.
        expire() -> None:
            Permanently remove all keys whose TTL has elapsed; must be called explicitly.

    """

    # Enforced public class variables
    storesystem: ClassVar[StoreSystem] = StoreSystem.FILE
    platform: ClassVar[Platform] = Platform.LOCAL

    # Enforced private class variables
    # Lock registry keyed by resolved path
    # shared by every instance pointing at the same file.
    _locks: ClassVar[dict[Path, threading.RLock]] = {}
    _locks_guard: ClassVar[threading.RLock] = threading.RLock()

    # Enforced instance variables
    # [Inherited] name: str
    # [Inherited] tags: dict[str, str]
    path: Path = Field(
        ...,
        description="[NoOps] Table file path, derived from the parent database path and name",
    )
    identity: LocalIdentity = Field(
        ...,
        description="[NoOps] Local identity associated with the table",
    )

    @property
    def _lock(self) -> threading.RLock:
        with self._locks_guard:
            _lock = self._locks.get(self.path)
            if _lock is None:
                _lock = threading.RLock()
                self._locks[self.path] = _lock
            return _lock

    @model_validator(mode="after")
    def _derive_path(self) -> "FileStoreTable":
        _p = IPath.resolve(value=self.path)
        if _p.exists() and not _p.is_file():
            raise ValueError(f"Path {_p} exists and must be a file")
        object.__setattr__(self, "path", _p)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "FileStoreTable":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=LocalIdentity.default(),
            platform=Platform.LOCAL,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    def write(
        self,
        key: str,
        data: Any,
        strict: bool = False,
    ) -> None:
        with self._lock:
            try:
                _content = self._load_content(strict=True)
            except Exception as e:
                self._handle_io_error(exception=e, strict=strict)
                return
            _content[key] = self._wrap(key=key, data=data)
            try:
                _stringfied: str = json.dumps(_content, ensure_ascii=False)
                _bytes: bytes = _stringfied.encode("utf-8")
                LocalObjectClient.write_bytes(self.path, _bytes)
            except Exception as e:
                self._handle_io_error(exception=e, strict=strict)

    def read(
        self,
        key: str | None = None,
        strict: bool = False,
    ) -> Any:
        with self._lock:
            _content = self._load_content(strict=strict)
            if key is None:
                return {_k: _v.get("data") for _k, _v in _content.items()}
            else:
                _envelope = _content.get(key)
                return _envelope.get("data") if _envelope is not None else None

    def delete(
        self,
        key: str,
        strict: bool = False,
    ) -> None:
        with self._lock:
            try:
                _content = self._load_content(strict=True)
            except Exception as e:
                self._handle_io_error(exception=e, strict=strict)
                return
            if key in _content:
                try:
                    del _content[key]
                    _stringfied: str = json.dumps(_content, ensure_ascii=False)
                    _bytes: bytes = _stringfied.encode("utf-8")
                    LocalObjectClient.write_bytes(self.path, _bytes)
                except Exception as e:
                    self._handle_io_error(exception=e, strict=strict)
            else:
                _error: KeyError = KeyError(f"Key {key} does not exist")
                self._handle_io_error(exception=_error, strict=strict)

    def expire(self) -> None:
        with self._lock:
            # Strict load: a corrupted file must raise, never be silently wiped by the rewrite below.
            _content: dict[str, Any] = self._load_content(strict=True)
            _now: float = IClock.current_timestamp(timezone="UTC")
            _filtered = {}
            for _k, _v in _content.items():
                if not self._is_expired(_v, _now):
                    _filtered[_k] = _v
            if len(_filtered) == len(_content):
                return
            _stringfied: str = json.dumps(_filtered, ensure_ascii=False)
            _bytes: bytes = _stringfied.encode("utf-8")
            LocalObjectClient.write_bytes(self.path, _bytes)

    def _load_content(
        self,
        strict: bool = False,
    ) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            _bytes: bytes = LocalObjectClient.read_bytes(self.path)
            return json.loads(_bytes)
        except Exception as e:
            self._handle_io_error(exception=e, strict=strict)
            return {}
