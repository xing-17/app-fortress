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
    OSS 存储表，直接位于其父数据库前缀下的单个 JSON 对象。
    仅可通过 `OSSStoreDatabase.table(name)` 构建。

    Args:
        name (str): Table 名称，单路径段
        bucket (str): OSS bucket名称
        region (str): OSS bucket所在区域
        key (str): Table 对象的 key，由父数据库前缀和表名派生
        in_vpc (bool): 是否在VPC内访问OSS
        identity (AliyunIdentity): 与表关联的 Aliyun 身份
        storesystem (Literal[StoreSystem.OSS]): 存储系统类型，固定为 OSS
        platform (Literal[Platform.ALIYUN]): 存储平台类型，固定为 ALIYUN
        tags (dict[str, str]): 表标签
        ttl_hours (float | None): 写入该表的键的默认 TTL（小时）

    Attributes:
        client (OSSClient): 按bucket/region/identity/in_vpc懒解析并缓存的OSS客户端实例。

    Methods:
        write(key: str, data: Any, strict: bool = False) -> None:
            写入或更新指定 key 的数据，数据会被封装在 {data, key, written_at, ttl} 结构中。
        read(key: str | None = None, strict: bool = False) -> Any:
            读取指定 key 的解封装数据，如果 key 为 None，则读取所有解封装数据。
        delete(key: str, strict: bool = False) -> None:
            删除指定 key 的值；如果 key 不存在且 strict 为 True，则抛出 KeyError。
        expire() -> None:
            永久移除所有 TTL 已过的键；必须显式调用。

    """

    storesystem: Literal[StoreSystem.OSS] = StoreSystem.OSS
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    bucket: str = Field(
        ...,
        description="[NoOps] OSS bucket名称",
    )
    region: str = Field(
        ...,
        description="[NoOps] OSS bucket所在区域",
    )
    key: str = Field(
        ...,
        description="[NoOps] Table 对象的 key，由父数据库前缀和表名派生",
    )
    in_vpc: bool = Field(
        default=False,
        description="[NoOps] 是否在VPC内访问OSS",
    )
    identity: AliyunIdentity = Field(
        ...,
        description="[NoOps] 与表关联的 Aliyun 身份",
    )

    # 按 (bucket, region, key) 为键的锁注册表，指向同一对象的所有实例共享同一把锁。
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
            # 严格加载：损坏的对象必须抛出异常，不能被下面的重写操作静默清空。
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
