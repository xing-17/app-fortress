from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, ClassVar

from pydantic import Field, model_validator

from app.internal.constant.assetfilekind import AssetFileKind
from app.internal.constant.assetfilesystem import AssetFilesystem
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.internal.util.partition import IPartition
from app.internal.util.prefix import IPrefix
from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.identity.aliyun import AliyunIdentity


class OSSAssetfile(BaseAssetfile):
    """
    OSS assetfile，表示OSS bucket中key对应的单个object。

    Attributes:
    ----------
        uri (str):
            OSS assetfile的URI
        frn (str):
            OSS assetfile的FRN
        stem (str):
            不含扩展名的文件名
        extension (str):
            文件扩展名
        name (str):
            包含扩展名的完整文件名
        client (OSSClient):
            按bucket/region/identity/in_vpc懒解析并缓存的OSS客户端实例

    Args:
    ----------
        bucket (str):
            OSS bucket名称
        region (str):
            OSS bucket所在区域
        key (str):
            OSS bucket key非空路径
        in_vpc (bool):
            是否在VPC内访问OSS，默认False
        identity (AliyunIdentity | str | None):
            OSS 身份认证
        filesystem (Literal[AssetFilesystem.OSS]):
            固定为AssetFilesystem.OSS
        platform (Literal[Platform.ALIYUN]):
            固定为Platform.ALIYUN
        filekind (AssetFileKind):
            未显式提供时，从key的后缀推导得出
        partitions (dict[str, str]):
            未显式提供时，从形如"key=value"的路径分段推导得出
        size (int | None):
            文件大小(字节)
        modified_at (float | None):
            文件最后修改时间
        metadata (dict[str, Any]):
            原始的OSS object元数据
        tags (dict[str, str]):
            OSS assetfile标签

    Methods:
    ----------
        read_bytes() -> bytes:
            从OSS读取assetfile内容；若key不存在则抛出FileNotFoundError。
        write_bytes(data: bytes) -> None:
            将字节数据写入assetfile对应的OSS key。
        load() -> None:
            从OSS object的HEAD元数据刷新size/modified_at/metadata。

    Example:
    ----------
        >>> assetfile = asset.assetfile("data.csv", partitions={"year": "2026", "month": "01"})
        >>> assetfile.write_bytes(b"col1,col2\\n1,2\\n")
        >>> assetfile.partitions
        {'year': '2026', 'month': '01'}

    """

    # Enforced public class variables
    filesystem: ClassVar[AssetFilesystem] = AssetFilesystem.OSS
    platform: ClassVar[Platform] = Platform.ALIYUN

    # Enforced instance variables
    # [Inherited] filekind: AssetFileKind
    # [Inherited]  partitions: dict[str, str]
    # [Inherited] size: int | None
    # [Inherited] modified_at: float | None
    # [Inherited] metadata: dict[str, Any]
    # [Inherited] tags: dict[str, Any]
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
    in_vpc: bool = Field(
        default=False,
        description="[Optional] 是否在VPC内访问OSS",
    )
    identity: AliyunIdentity | str | None = Field(
        default_factory=AliyunIdentity.default,
        description="[Optional] OSS 身份认证",
    )

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
    def client(self) -> OSSClient:
        return OSSClient.get_client(
            bucket=self.bucket,
            region=self.region,
            identity=self.identity,
            in_vpc=self.in_vpc,
        )

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
        return IFrn.resolve(
            [
                "assetfile",
                f"platform={self.platform}",
                f"bucket={self.bucket}",
                f"key={self.key}",
            ]
        )

    @property
    def name(self) -> str:
        return PurePosixPath(self.key).name

    def read_bytes(self) -> bytes:
        return self.client.read_bytes(self.key)

    def write_bytes(
        self,
        data: bytes,
    ) -> None:
        self.client.write_bytes(
            key=self.key,
            data=data,
        )

    def load(self) -> None:
        _meta: dict[str, Any] = self.client.get_object(self.key)
        if _meta:
            _origin: dict[str, Any] = dict(self.metadata)
            _update: dict = {
                "etag": _meta.get("etag"),
                "last_modified": _meta.get("last_modified"),
                "size": _meta.get("size"),
                "storage_class": _meta.get("storage_class"),
            }
            _origin.update(_update)
            object.__setattr__(self, "metadata", _origin)
        _last_modified: float | None = _meta.get("last_modified")
        if _last_modified:
            object.__setattr__(self, "modified_at", _last_modified)
        _size: int | None = _meta.get("size")
        if _size:
            object.__setattr__(self, "size", _size)
