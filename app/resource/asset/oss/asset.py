from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import Field, model_validator

from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.prefix import IPrefix
from app.resource._client.oss.client import OSSClient
from app.internal.util.frn import IFrn
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._asset import BaseAsset
from app.resource.asset.oss.assetfile import OSSAssetfile
from app.resource.identity.aliyun import AliyunIdentity


class OSSAsset(BaseAsset):
    """
    OSS asset contains a collection of OSS assetfiles.

    Args:
        bucket (str): OSS bucket名称
        region (str): OSS bucket所在区域
        prefix (str): OSS bucket前缀(默认空字符串)
        in_vpc (bool): 是否在VPC内访问OSS (默认False)
        identity (AliyunIdentity | str | None): OSS 身份认证
        filesystem (Literal[AssetFilesystem.OSS]): 固定为AssetFilesystem.OSS
        platform (Literal[Platform.ALIYUN]): 固定为Platform.ALIYUN
        tags (dict[str, str]): OSS asset标签

    Attributes:
        client (OSSClient): 按bucket/region/identity/in_vpc懒解析并缓存的OSS客户端实例。

    Methods:
        list_assetfiles(since=None, until=None, recursive=True) -> list[OSSAssetfile]:
            List assetfiles under the bucket/prefix matching full_pattern, optionally filtered by modified time.
        list_objects(pattern=None, since=None, until=None, recursive=True) -> list[OSSAssetfile]:
            List assetfiles under the bucket/prefix matching pattern, optionally filtered by modified time.

    """

    # Inherited from BaseAsset
    # - filekind (AssetFileKind): Asset file kind, default is AssetFileKind.OBJECT
    # - partitions (list[str]): Partition keys for the asset
    # - tags (dict[str, str]): Asset tags
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
    filesystem: Literal[AssetFilesystem.OSS] = AssetFilesystem.OSS
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN

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
            )
            _files.append(_assetfile)
        return _files
