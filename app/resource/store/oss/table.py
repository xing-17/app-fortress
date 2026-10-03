from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.prefix import IPrefix
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._base import BaseIdentity
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

    Attributes:
        client (OSSClient): 按bucket/region/identity/in_vpc懒解析并缓存的OSS客户端实例。

    Methods:
        write(key: str, data: Any, strict: bool = False) -> None:
            Upsert data for key into the table's flat {key: data} JSON content.
        read(key: str, strict: bool = False) -> Any:
            Read data for key, or None if missing.
        delete(key: str, strict: bool = False) -> None:
            Delete a key's value; raises KeyError if missing and strict is True.

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
        _content = self._load_content(strict=strict)
        _content[key] = data
        try:
            _stringfied: str = json.dumps(_content, ensure_ascii=False)
            _bytes: bytes = _stringfied.encode("utf-8")
            self.client.write_bytes(self.key, _bytes)
        except Exception as e:
            self._handle_io_error(exception=e, strict=strict)

    def read(
        self,
        key: str,
        strict: bool = False,
    ) -> Any:
        _content = self._load_content(strict=strict)
        return _content.get(key)

    def delete(
        self,
        key: str,
        strict: bool = False,
    ) -> None:
        _content = self._load_content(strict=strict)
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

    def _load_content(
        self,
        strict: bool = False,
    ) -> dict[str, Any]:
        try:
            _bytes: bytes = self.client.read_bytes(self.key)
        except FileNotFoundError:
            return {}
        try:
            return json.loads(_bytes)
        except Exception as e:
            self._handle_io_error(exception=e, strict=strict)
            return {}

    def export(self) -> dict[str, Any]:
        _result: dict = super().export()
        _result["identity"] = self.identity.name
        return _result
