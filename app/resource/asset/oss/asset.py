from __future__ import annotations

import posixpath
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, ClassVar

from pydantic import Field, model_validator

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.internal.util.partition import IPartition
from app.internal.util.prefix import IPrefix
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._asset import BaseAsset
from app.resource.asset.oss.assetfile import OSSAssetfile
from app.resource.identity.aliyun import AliyunIdentity


class OSSAsset(BaseAsset):
    """
    OSS asset，表示一组OSS assetfile的集合，可选择按分区划分前缀路径。

    Attributes:
    ----------
        uri (str):
            OSS asset的URI
        frn (str):
            OSS asset的FRN
        name (str):
            OSS asset名称(取自prefix末段)
        object_pattern (str):
            按filekind匹配文件的glob pattern
        partition_pattern (str):
            匹配分区子目录的glob pattern
        full_pattern (str):
            匹配该asset下assetfile的完整glob pattern
        client (OSSClient):
            按bucket/region/identity/in_vpc懒解析并缓存的OSS客户端实例

    Args:
    ----------
        bucket (str):
            OSS bucket名称
        region (str):
            OSS bucket所在区域
        prefix (str):
            OSS bucket前缀，默认空字符串
        in_vpc (bool):
            是否在VPC内访问OSS，默认False
        identity (AliyunIdentity | str | None):
            OSS 身份认证
        filesystem (Literal[AssetFilesystem.OSS]):
            固定为AssetFilesystem.OSS
        platform (Literal[Platform.ALIYUN]):
            固定为Platform.ALIYUN
        filekind (AssetFileKind):
            asset文件类型，默认AssetFileKind.OBJECT
        partitions (list[str]):
            该asset声明的分区键(如["year", "month"])
        tags (dict[str, str]):
            OSS asset标签

    Methods:
    ----------
        list_assetfiles(since=None, until=None, recursive=True) -> list[OSSAssetfile]:
            列出bucket/prefix下匹配full_pattern的assetfile，可选按修改时间过滤。
        list_objects(pattern=None, since=None, until=None, recursive=True) -> list[OSSAssetfile]:
            列出bucket/prefix下匹配任意pattern的assetfile。
        assetfile(name, partitions=None) -> OSSAssetfile:
            在该asset下构造一个OSSAssetfile，分区键与声明不一致时拒绝。

    Example:
    ----------
        >>> vault = OSSVault.from_setting(OSSVaultSetting(name="my_vault", bucket="my-bucket", region="cn-hangzhou"))
        >>> asset = vault.asset("prices", partitions=["year", "month"])
        >>> assetfile = asset.assetfile("data.csv", partitions={"year": "2026", "month": "01"})

    """

    # Enforced public class variables
    filesystem: ClassVar[AssetFilesystem] = AssetFilesystem.OSS
    platform: ClassVar[Platform] = Platform.ALIYUN

    # Enforced instance variables
    # [Inherited] filekind: AssetFileKind
    # [Inherited] partitions: list[str]
    # [Inherited] tags: dict[str, str]
    bucket: str = Field(
        ...,
        description="[Required] OSS bucket名称",
    )
    region: str = Field(
        ...,
        description="[Required] OSS bucket所在区域",
    )
    prefix: str = Field(
        default="",
        description="[Optional] OSS bucket前缀",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] 是否在VPC内访问OSS",
    )
    identity: AliyunIdentity | str | None = Field(
        default_factory=AliyunIdentity.default,
        description="[Optional] OSS 身份认证",
    )

    @model_validator(mode="after")
    def _derive_prefix(self) -> "OSSAsset":
        _p = IPrefix.resolve(self.prefix)
        object.__setattr__(self, "prefix", _p)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "OSSAsset":
        _value: AliyunIdentity | str | None = self.identity
        _identity: AliyunIdentity = GlobalIdentities.resolve(
            value=_value,
            platform=Platform.ALIYUN,
            default=AliyunIdentity.default(),
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

    @property
    def uri(self) -> str:
        return f"oss://{self.bucket}/{self.prefix}"

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "asset",
                f"platform={self.platform}",
                f"bucket={self.bucket}",
                f"prefix={self.prefix}",
            ]
        )

    @property
    def name(self) -> str:
        return PurePosixPath(self.prefix).name

    # @property: object_pattern from BaseAsset

    # @property: partition_pattern from BaseAsset

    @property
    def full_pattern(self) -> str:
        _obj_expr: str = self.object_pattern
        _base_expr: str = f"{self.prefix}"
        if not self.partitions:
            return f"*{_base_expr}/{_obj_expr}"
        else:
            return f"*{_base_expr}/{self.partition_pattern}/{_obj_expr}"

    def list_assetfiles(
        self,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        recursive: bool = True,
    ) -> list["OSSAssetfile"]:
        return self.list_objects(
            pattern=self.full_pattern,
            since=since,
            until=until,
            recursive=recursive,
        )

    def list_objects(
        self,
        pattern: str | None = None,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        recursive: bool = True,
    ) -> list["OSSAssetfile"]:
        _files: list["OSSAssetfile"] = []
        _targets: list[dict[str, Any]] = self.client.list_objects(
            prefix=self.prefix,
            pattern=pattern,
            since=since,
            until=until,
            recursive=recursive,
        )
        for _meta in _targets:
            _last_modified: float | None = _meta.get("last_modified")
            _size: int | None = _meta.get("size")
            _o_meta: dict[str, Any] = {
                "etag": _meta.get("etag"),
                "last_modified": _last_modified,
                "size": _size,
                "storage_class": _meta.get("storage_class"),
            }
            _o_meta: dict[str, Any] = {k: v for k, v in _o_meta.items() if v is not None}
            _assetfile: OSSAssetfile = OSSAssetfile(
                bucket=self.bucket,
                region=self.region,
                key=_meta["key"],
                identity=self.identity,
                metadata=_o_meta,
                modified_at=_last_modified,
                size=_size,
                tags=self.tags,
                in_vpc=self.in_vpc,
                _authorized=True,
            )
            _files.append(_assetfile)
        return _files

    def assetfile(
        self,
        name: str,
        partitions: dict[str, str] | None = None,
    ) -> "OSSAssetfile":
        _partitions: dict[str, str] = partitions or {}

        # Ensure partitions are consistent
        _ptn_keys: set[str] = set(_partitions.keys())
        if _ptn_keys != set(self.partitions):
            raise ValueError(f"Partitions must be {self.partitions}, got {list(_ptn_keys)}")

        # Construct the full key for the assetfile
        _ordered: dict[str, str] = {k: _partitions[k] for k in self.partitions}
        _rel: str = IPartition.to_string(_ordered)
        _segments: list[str] = [self.prefix, *([_rel] if _rel else []), name]
        _full_key: str = posixpath.join(*_segments)

        _assetfile: OSSAssetfile = OSSAssetfile(
            bucket=self.bucket,
            region=self.region,
            key=_full_key,
            identity=self.identity,
            tags=self.tags,
            in_vpc=self.in_vpc,
            _authorized=True,
        )
        if _assetfile.filekind != self.filekind:
            raise ValueError(f"Assetfile must be {self.filekind}, got {_assetfile.filekind}")
        return _assetfile
