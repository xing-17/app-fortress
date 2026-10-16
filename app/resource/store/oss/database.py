from __future__ import annotations

import posixpath
from pathlib import PurePosixPath
from typing import ClassVar

from pydantic import Field, model_validator

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.internal.util.frn import IFrn
from app.internal.util.prefix import IPrefix
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.aliyun import AliyunIdentity
from app.resource.store._common._database import BaseDatabase
from app.resource.store.oss.table import OSSStoreTable
from app.setting._identity import AliyunIdentitySetting


class OSSStoreDatabase(BaseDatabase):
    """
    OSS store database backed by a single prefix under the parent store prefix.

    Attributes:
    ----------
        storesystem (StoreSystem):
            Store system type, fixed as OSS.
        platform (Platform):
            Store platform type, fixed as ALIYUN.
        client (OSSClient):
            OSS client resolved and cached by bucket/region/identity/in_vpc.

    Args:
    ----------
        name (str):
            Database name, single path segment.
        bucket (str):
            OSS bucket name
        region (str):
            OSS bucket region
        prefix (str):
            Database prefix, derived from the parent store prefix and name.
        in_vpc (bool):
            Whether to access OSS from within a VPC
        identity (AliyunIdentity):
            Aliyun identity associated with the database.
        tags (dict[str, str]):
            Database tags

    Methods:
    ----------
        list_tables() -> list[OSSStoreTable]:
            Enumerate the *.json tables that currently exist directly under this database.
        table(name: str, ttl_hours: float | None = None, max_items: int | None = None) -> OSSStoreTable:
            Only entry point for building a table under this database.
        delete(name: str, strict: bool = False) -> None:
            Delete a table's JSON object by name; raises FileNotFoundError if missing and strict is True.

    """

    # Enforced public class variables
    storesystem: ClassVar[StoreSystem] = StoreSystem.OSS
    platform: ClassVar[Platform] = Platform.ALIYUN

    # Enforced instance variables
    # [Inherited] name: str
    # [Inherited] tags: dict[str, str]
    bucket: str = Field(
        ...,
        description="[NoOps] OSS bucket name",
    )
    region: str = Field(
        ...,
        description="[NoOps] OSS bucket region",
    )
    prefix: str = Field(
        ...,
        description="[NoOps] Database prefix, derived from the parent store prefix and name",
    )
    in_vpc: bool = Field(
        default=False,
        description="[NoOps] Whether to access OSS from within a VPC",
    )
    identity: AliyunIdentity | AliyunIdentitySetting | str | None = Field(
        ...,
        description="[NoOps] Aliyun identity associated with the database",
    )

    @model_validator(mode="after")
    def _derive_prefix(self) -> "OSSStoreDatabase":
        _p = IPrefix.resolve(value=self.prefix)
        object.__setattr__(self, "prefix", _p)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "OSSStoreDatabase":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=AliyunIdentity.default(),
            platform=Platform.ALIYUN,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "store",
                "database",
                f"platform={self.platform}",
                f"storesystem={self.storesystem}",
                f"bucket={self.bucket}",
                f"prefix={self.prefix}",
            ]
        )

    @property
    def client(self) -> OSSClient:
        return OSSClient.get_client(
            bucket=self.bucket,
            region=self.region,
            identity=self.identity,
            in_vpc=self.in_vpc,
        )

    def list_tables(self) -> list[OSSStoreTable]:
        _tables: list[OSSStoreTable] = []
        _objects = self.client.list_objects(
            prefix=f"{self.prefix}/",
            pattern="*.json",
            recursive=False,
        )
        for _object in _objects:
            _table: OSSStoreTable = OSSStoreTable(
                name=PurePosixPath(_object["key"]).stem,
                bucket=self.bucket,
                region=self.region,
                key=_object["key"],
                in_vpc=self.in_vpc,
                identity=self.identity,
                _authorized=True,
            )
            _tables.append(_table)
        return _tables

    def table(
        self,
        name: str,
        ttl_hours: float | None = None,
        max_items: int | None = None,
    ) -> OSSStoreTable:
        return OSSStoreTable(
            name=name,
            bucket=self.bucket,
            region=self.region,
            key=posixpath.join(self.prefix, f"{name}.json"),
            in_vpc=self.in_vpc,
            identity=self.identity,
            ttl_hours=ttl_hours,
            max_items=max_items,
            _authorized=True,
        )

    def delete(
        self,
        name: str,
        strict: bool = False,
    ) -> None:
        _key: str = posixpath.join(self.prefix, f"{name}.json")
        try:
            self.client.get_object(_key)
        except FileNotFoundError:
            if strict:
                raise FileNotFoundError(f"Table {name} does not exist at prefix {self.prefix}")
            return
        self.client.delete_object(_key)
