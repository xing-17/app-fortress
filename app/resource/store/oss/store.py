from __future__ import annotations

import posixpath
from pathlib import PurePosixPath
from typing import ClassVar

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.prefix import IPrefix
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.aliyun import AliyunIdentity
from app.resource.store._common._store import BaseStore
from app.resource.store.oss.database import OSSStoreDatabase
from app.resource.store.oss.table import OSSStoreTable
from app.setting._identity import AbstractIdentitySetting
from app.setting._store import OSSStoreSetting


class OSSStore(BaseStore):
    """
    OSS store backed by Aliyun Object Storage Service.

    Attributes:
    ----------
        storesystem (StoreSystem):
            Store system type, fixed as OSS.
        platform (Platform):
            Store platform type, fixed as ALIYUN.
        uri (str):
            Store location, formatted as oss://<bucket>/<prefix>.
        client (OSSClient):
            OSS client resolved and cached by bucket/region/identity/in_vpc.

    Args:
    ----------
        name (str):
            Store name
        bucket (str):
            OSS bucket name
        region (str):
            OSS bucket region
        prefix (str | None):
            OSS bucket prefix, default store
        in_vpc (bool):
            Whether to access OSS from within a VPC, default False
        identity (AliyunIdentity | AbstractIdentitySetting | str | None):
            Aliyun identity associated with the OSS store
        tags (dict[str, str]):
            Store tags

    Methods:
    ----------
        from_setting(cls, setting: OSSStoreSetting) -> OSSStore:
            Create an OSSStore instance from an OSSStoreSetting object.
        list_databases() -> list[OSSStoreDatabase]:
            Enumerate databases that currently exist under the store prefix.
        database(name: str) -> OSSStoreDatabase:
            Only entry point for building a database under this store.
        table(database: str, name: str, ttl_hours: float | None = None) -> OSSStoreTable:
            Only entry point for building a table under a database of this store.

    Example:
    ----------
        >>> from app.resource.store.oss.store import OSSStore
        >>> store = OSSStore(name="my_store", bucket="my-bucket", region="cn-hangzhou")
        >>> store.uri
        'oss://my-bucket/store'

    """

    # Enforced public class variables
    storesystem: ClassVar[StoreSystem] = StoreSystem.OSS
    platform: ClassVar[Platform] = Platform.ALIYUN

    # Enforced instance variables
    # [Inherited] name: str
    # [Inherited] tags: dict[str, str]
    bucket: str = Field(
        ...,
        description="[Required] OSS bucket name",
    )
    region: str = Field(
        ...,
        description="[Required] OSS bucket region",
    )
    prefix: str | None = Field(
        default=None,
        description="[Optional] OSS bucket prefix",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] Whether to access OSS from within a VPC",
    )
    identity: AliyunIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] Aliyun identity associated with the OSS store",
    )

    # Class-level attributes
    default_prefix: ClassVar[str] = "store"

    @model_validator(mode="after")
    def _derive_prefix(self) -> "OSSStore":
        _p = IPrefix.resolve(
            value=self.prefix,
            default=self.default_prefix,
        )
        object.__setattr__(self, "prefix", _p)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "OSSStore":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=AliyunIdentity.default(),
            platform=Platform.ALIYUN,
        )
        object.__setattr__(self, "identity", _identity)
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

    def list_databases(self) -> list[OSSStoreDatabase]:
        _databases: list[OSSStoreDatabase] = []
        _folders = self.client.list_folders(
            prefix=f"{self.prefix}/",
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
        _database: OSSStoreDatabase = OSSStoreDatabase(
            name=name,
            bucket=self.bucket,
            region=self.region,
            prefix=posixpath.join(self.prefix, name),
            in_vpc=self.in_vpc,
            identity=self.identity,
            _authorized=True,
        )
        return _database

    def table(
        self,
        database: str,
        name: str,
        ttl_hours: float | None = None,
    ) -> OSSStoreTable:
        _database: OSSStoreDatabase = self.database(database)
        _table: OSSStoreTable = _database.table(
            name=name,
            ttl_hours=ttl_hours,
        )
        return _table
