from __future__ import annotations

import posixpath
from pathlib import PurePosixPath
from typing import ClassVar, Literal

from pydantic import Field, PrivateAttr, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.prefix import IPrefix
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._base import BaseIdentity
from app.resource.identity.aliyun import AliyunIdentity
from app.resource.store._common._store import BaseStore
from app.resource.store.oss.database import OSSStoreDatabase
from app.resource.store.oss.table import OSSStoreTable
from app.setting._identity import AbstractIdentitySetting
from app.setting._store import OSSStoreSetting


class OSSStore(BaseStore):
    """
    OSS store backed by Aliyun Object Storage Service.

    Args:
        name (str): Store name
        bucket (str): OSS bucket名称
        region (str): OSS bucket所在区域
        prefix (str | None): OSS bucket前缀(默认store)
        in_vpc (bool): 是否在VPC内访问OSS(默认False)
        identity (AliyunIdentity | AbstractIdentitySetting | str | None): Aliyun身份(默认AliyunIdentity.default())
        storesystem (Literal[StoreSystem.OSS]): Store system类型(固定为StoreSystem.OSS)
        platform (Literal[Platform.ALIYUN]): Store platform类型(固定为Platform.ALIYUN)
        tags (dict[str, str]): Store标签

    Attributes:
        client (OSSClient): 按bucket/region/identity/in_vpc懒解析并缓存的OSS客户端实例。
        databases (list[OSSStoreDatabase]): Lazily loaded and cached list of databases under the store.

    Methods:
        from_setting(cls, setting: OSSStoreSetting) -> OSSStore:
            Create an OSSStore instance from an OSSStoreSetting object.
        database(name: str) -> OSSStoreDatabase:
            Only entry point for building a database under this store.
        list_databases() -> list[OSSStoreDatabase]:
            Enumerate databases that currently exist under the store prefix.
        load_databases(force: bool = False) -> list[OSSStoreDatabase]:
            Load (and cache) the databases list, re-scanning when force is True.
        reset_databases() -> None:
            Clear the cached databases list.
        table(database: str, name: str) -> OSSStoreTable:
            Retrieve a table under the specified database in this store.

    Example:
        >>> from app.resource.store.oss.store import OSSStore
        >>> store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou")
        >>> store.uri
        'oss://my-bucket/store'

    """

    # Inherited from BaseStore
    # - name: str
    # - tags: dict[str, Any]
    storesystem: Literal[StoreSystem.OSS] = StoreSystem.OSS
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN
    bucket: str = Field(
        ...,
        description="[Required] OSS bucket name",
    )
    region: str = Field(
        ...,
        description="[Required] OSS bucket所在区域",
    )
    prefix: str | None = Field(
        default=None,
        description="[Optional] OSS bucket前缀",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] 是否在VPC内访问OSS",
    )
    identity: AliyunIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Identity used for this Aliyun store",
    )

    # Class-level attributes
    default_prefix: ClassVar[str] = "store"

    # List of databases under store
    _databases: list[OSSStoreDatabase] | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _derive_identity(self) -> "OSSStore":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=AliyunIdentity.default(),
            platform=Platform.ALIYUN,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @model_validator(mode="after")
    def _derive_prefix(self) -> "OSSStore":
        _p = IPrefix.resolve(
            value=self.prefix,
            default=self.default_prefix,
        )
        object.__setattr__(self, "prefix", _p)
        return self

    @model_validator(mode="after")
    def _derive_databases(self) -> "OSSStore":
        self.load_databases()
        return self

    @classmethod
    def from_setting(
        cls,
        setting: OSSStoreSetting,
    ) -> OSSStore:
        return cls(
            name=setting.name,
            bucket=setting.bucket,
            region=setting.region,
            prefix=setting.prefix,
            in_vpc=setting.in_vpc,
            identity=setting.identity,
            tags=setting.tags,
        )

    @property
    def uri(self) -> str:
        return f"oss://{self.bucket}/{self.prefix}"

    @property
    def client(self) -> OSSClient:
        return OSSClient.get_client(
            bucket=self.bucket,
            region=self.region,
            identity=self.identity,
            in_vpc=self.in_vpc,
        )

    @property
    def databases(self) -> list[OSSStoreDatabase]:
        self.load_databases()
        return self._databases

    def load_databases(
        self,
        force: bool = False,
    ) -> list[OSSStoreDatabase]:
        if force or self._databases is None:
            self._databases = self.list_databases()
        return self._databases

    def reset_databases(self) -> None:
        self._databases = None

    def list_databases(self) -> list[OSSStoreDatabase]:
        _databases: list[OSSStoreDatabase] = []
        _folders = self.client.list_folders(
            prefix=self.prefix,
            recursive=False,
        )
        for _folder in _folders:
            _prefix: str = _folder["prefix"]
            _database: OSSStoreDatabase = OSSStoreDatabase(
                name=PurePosixPath(_prefix.rstrip("/")).name,
                bucket=self.bucket,
                region=self.region,
                prefix=_prefix,
                in_vpc=self.in_vpc,
                identity=self.identity,
                _authorized=True,
            )
            _databases.append(_database)
        return _databases

    def database(
        self,
        name: str,
    ) -> OSSStoreDatabase:
        return OSSStoreDatabase(
            name=name,
            bucket=self.bucket,
            region=self.region,
            prefix=posixpath.join(self.prefix, name),
            in_vpc=self.in_vpc,
            identity=self.identity,
            _authorized=True,
        )

    def table(
        self,
        database: str,
        name: str,
    ) -> OSSStoreTable:
        _database: OSSStoreDatabase = self.database(database)
        _table: OSSStoreTable = _database.table(name)
        return _table
