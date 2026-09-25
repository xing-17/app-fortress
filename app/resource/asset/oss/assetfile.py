from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, model_validator

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.partition import IPartition
from app.internal.util.prefix import IPrefix
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.identity.aliyun.aliyun import AliyunIdentity


class OSSAssetfile(BaseAssetfile):
    """
    OSS assetfile as a single object at OSS bucket key

    Args:
        bucket (str): OSS bucket名称
        region (str): OSS bucket所在区域
        key (str): OSS bucket key非空路径
        identity (AliyunIdentity | str | None): OSS 身份认证
        filesystem (Literal[AssetFilesystem.OSS]): 固定为AssetFilesystem.OSS
        platform (Literal[Platform.ALIYUN]): 固定为Platform.ALIYUN
        partitions (dict[str, str]): 从key解析出的分区键值对
        size (int | None): 文件大小(字节)
        modified_at (datetime | None): 最后修改时间
        metadata (dict[str, Any]): 元数据
        tags (dict[str, Any]): 标签

    """

    # Inherit from BaseAssetfile
    # - filekind: AssetFileKind
    # - partitions: dict[str, str]
    # - size: int | None
    # - modified_at: datetime | None
    # - metadata: dict[str, Any]
    # - tags: dict[str, Any]
    bucket: str = Field(
        ...,
        description="[Required] OSS bucket名称",
    )
    region: str = Field(
        ...,
        description="[Required] OSS bucket所在区域",
    )
    key: str = Field(
        ...,
        description="[Required] OSS bucket key非空路径",
    )
    identity: AliyunIdentity | str | None = Field(
        default_factory=AliyunIdentity.default,
        description="[Optional] OSS 身份认证",
    )
    filesystem: Literal[AssetFilesystem.OSS] = AssetFilesystem.OSS
    platform: Literal[Platform.ALIYUN] = Platform.ALIYUN

    @model_validator(mode="after")
    def _derive_key(self) -> "OSSAssetfile":
        IPrefix.validate_key(self.key)
        _key: str = IPrefix.resolve(self.key)
        object.__setattr__(self, "key", _key)
        return self

    @model_validator(mode="after")
    def _derive_identity(self) -> "OSSAssetfile":
        _identity: AliyunIdentity = GlobalIdentities.resolve(
            value=self.identity,
            platform=Platform.ALIYUN,
            default=AliyunIdentity.default(),
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @model_validator(mode="after")
    def _derive_partitions(self) -> "OSSAssetfile":
        if not self.partitions:
            _segs: list[str] = self.key.split("/")
            _parts: dict[str, str] = IPartition.resolve(_segs)
            if _parts:
                object.__setattr__(self, "partitions", _parts)
        return self

    @model_validator(mode="after")
    def _derive_filekind(self) -> "OSSAssetfile":
        _val: str = PurePosixPath(self.key).suffix.lstrip(".").strip().lower()
        for _member in AssetFileKind:
            if _member.value == _val:
                object.__setattr__(self, "filekind", _member)
                break
        else:
            object.__setattr__(self, "filekind", AssetFileKind.OBJECT)
        # tags were snapshotted before filekind was derived; resync now.
        self._update_tags()
        return self

    @property
    def uri(self) -> str:
        return f"oss://{self.bucket}/{self.key}"

    @property
    def stem(self) -> str:
        return PurePosixPath(self.key).stem

    @property
    def extension(self) -> str:
        return PurePosixPath(self.key).suffix.lstrip(".")

    @property
    def frn(self) -> str:
        return f"assetfile:{self.platform}:{self.bucket}/{self.key}"

    @property
    def name(self) -> str:
        return PurePosixPath(self.key).name
