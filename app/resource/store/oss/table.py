from __future__ import annotations

import json
import threading
from typing import Any, ClassVar, Literal

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.clock import IClock
from app.internal.util.prefix import IPrefix
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.aliyun import AliyunIdentity
from app.resource.store._common._table import BaseTable


class OSSStoreTable(BaseTable):
    """
    OSS store table backed by a single JSON object directly under its parent database's prefix.

    Only constructible via `OSSStoreDatabase.table(name)`.

    Args:
        name (str): Table name, single path segment
        bucket (str): OSS bucket名称
        region (str): OSS bucket所在区域
        key (str): Table object key, derived from the parent database prefix and name
        in_vpc (bool): 是否在VPC内访问OSS
        identity (AliyunIdentity): Aliyun identity associated with the table
        storesystem (Literal[StoreSystem.OSS]): Store system type, fixed as OSS
        platform (Literal[Platform.ALIYUN]): Store platform type, fixed as ALIYUN
        tags (dict[str, str]): Table tags
        ttl_hours (float | None): Default TTL in hours for keys written to this table

    Attributes:
        client (OSSClient): 按bucket/region/identity/in_vpc懒解析并缓存的OSS客户端实例。

    Methods:
        write(key: str, data: Any, strict: bool = False) -> None:
            Upsert data for key, wrapped in a {data, key, written_at, ttl} envelope.
        read(key: str | None = None, strict: bool = False) -> Any:
            Read the unwrapped data for key, or all unwrapped data if key is None.
        delete(key: str, strict: bool = False) -> None:
            Delete a key's value; raises KeyError if missing and strict is True.
        expire() -> None:
            Permanently remove all keys whose TTL has elapsed; must be called explicitly.

    """

    storesystem: Literal[StoreSystem.OSS] = StoreSystem.OSS
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    bucket: str = Field(
        ...,
        description="[NoOps] OSS bucket name",
    )
    region: str = Field(
        ...,
        description="[NoOps] OSS bucket所在区域",
    )
    key: str = Field(
        ...,
        description="[NoOps] Table object key, derived from the parent database prefix and name",
    )
    in_vpc: bool = Field(
        default=False,
        description="[NoOps] 是否在VPC内访问OSS",
    )
    identity: AliyunIdentity = Field(
        ...,
        description="[NoOps] Aliyun identity associated with the table",
    )

    # Lock registry keyed by (bucket, region, key), shared by every instance pointing at the same object.
    _locks: ClassVar[dict[tuple[str, str, str], threading.RLock]] = {}
    _locks_guard: ClassVar[threading.RLock] = threading.RLock()

    @property
    def _lock(self) -> threading.RLock:
        _resource_key = (self.bucket, self.region, self.key)
        with self._locks_guard:
            _lock = self._locks.get(_resource_key)
            if _lock is None:
                _lock = threading.RLock()
                self._locks[_resource_key] = _lock
            return _lock

    @model_validator(mode="after")
    def _derive_key(self) -> "OSSStoreTable":
        IPrefix.validate_key(self.key)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "OSSStoreTable":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=AliyunIdentity.default(),
            platform=Platform.ALIYUN,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @property
    def client(self) -> OSSClient:
        return OSSClient.get_client(
            bucket=self.bucket,
            region=self.region,
            identity=self.identity,
            in_vpc=self.in_vpc,
        )

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
                self.client.write_bytes(self.key, _bytes)
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
                _result = {}
                for _k, _v in _content.items():
                    _result[_k] = _v.get("data")
                return _result
            else:
                _envelope = _content.get(key)
                if _envelope is None:
                    return None
                else:
                    return _envelope.get("data")

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
                    self.client.write_bytes(self.key, _bytes)
                except Exception as e:
                    self._handle_io_error(exception=e, strict=strict)
            else:
                _error: KeyError = KeyError(f"Key {key} does not exist")
                self._handle_io_error(exception=_error, strict=strict)

    def expire(self) -> None:
        with self._lock:
            # Strict load: a corrupted object must raise, never be silently wiped by the rewrite below.
            _content = self._load_content(strict=True)
            _now: float = IClock.current_timestamp(timezone="UTC")
            _filtered: dict[str, Any] = {}
            for _k, _v in _content.items():
                if not self._is_expired(_v, _now):
                    _filtered[_k] = _v
            if len(_filtered) == len(_content):
                return
            _stringfied: str = json.dumps(_filtered, ensure_ascii=False)
            _bytes: bytes = _stringfied.encode("utf-8")
            self.client.write_bytes(self.key, _bytes)

    def _load_content(
        self,
        strict: bool = False,
    ) -> dict[str, Any]:
        try:
            _bytes: bytes = self.client.read_bytes(self.key)
            return json.loads(_bytes)
        except FileNotFoundError:
            return {}
        except Exception as e:
            self._handle_io_error(exception=e, strict=strict)
            return {}

    def export(self) -> dict[str, Any]:
        _result: dict = super().export()
        _result["identity"] = self.identity.name
        return _result
