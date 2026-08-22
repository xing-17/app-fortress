from __future__ import annotations

import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from pydantic import Field, computed_field

from bastion._internal.object import IBastionObject
from bastion.control.asset.base.base import IAssetLike
from bastion.control.asset.base.factory import AssetFactory
from bastion.domain.asset import BaseAssetModel
from bastion.domain.assetref import BaseAssetRefModel
from bastion.domain.platform import Platform
from bastion.control.asset.oss.adaptor import IOSSAdaptorLike, OSSAdaptor


class _OSSObjectMixin:
    def _parse_oss_uri(self, uri: str) -> tuple[str, str]:
        parsed = urlparse(uri)
        if parsed.scheme != "oss":
            raise ValueError(f"Invalid OSS URI: {uri}")
        bucket = parsed.netloc
        prefix = parsed.path.lstrip("/")
        return bucket, prefix


class OSSAssetRef(
    BaseAssetRefModel,
    _OSSObjectMixin,
):
    """
    An OSS object reference in Alibaba Cloud OSS storage.

    Attributes:
        uri: OSS URI of the object (e.g., oss://bucket-name/path/to/object)
        size: Size of the object in bytes
        modified_at: Last modified timestamp of the object
        partitions: Partition values extracted from the OSS key (if applicable)
        region: Alibaba Cloud region of the OSS bucket

    """

    region: str | None = Field(
        default=None,
        description="Region of the OSS bucket",
    )
    
    @computed_field
    @property
    def bucket(self) -> str:
        bucket, _ = self._parse_oss_uri(self.uri)
        return bucket

    @computed_field
    @property
    def prefix(self) -> str:
        _, prefix = self._parse_oss_uri(self.uri)
        return prefix


class OSSAssetModel(
    BaseAssetModel,
    _OSSObjectMixin,
):
    """
    Domain model for OSS assets.

    Attributes:
        name (str): Asset name.
        kind (AssetKind): Asset kind (parquet, csv, etc.).
        uri (str): OSS URI of the asset (e.g., oss://bucket-name/path/to/object).
        region (str): Alibaba Cloud region of the OSS bucket.
        endpoint (str | None): Optional custom OSS endpoint URL.
        partitions (list[str]): Partition column names.
        refs (list[BaseAssetRefModel]): Asset references.
        description (str | None): Optional description.
        owner (str | None): Optional owner identifier.
        metadata (dict[str, Any]): Arbitrary metadata.
        tags (dict[str, str]): Tag key-value pairs.
        bucket (str): Computed from uri - the OSS bucket name.
        prefix (str): Computed from uri - the OSS object key/path.

    """

    platform: Platform = Platform.OSS
    uri: str = Field(
        ...,
        description="OSS URI of the asset (e.g., oss://bucket-name/path/to/object)",
    )
    region: str = Field(
        ...,
        description="Region of the OSS bucket",
    )
    endpoint: str | None = Field(
        default=None,
        description="Endpoint URL for OSS (e.g., oss-cn-hangzhou.aliyuncs.com)",
    )

    @computed_field
    @property
    def bucket(self) -> str:
        bucket, _ = self._parse_oss_uri(self.uri)
        return bucket

    @computed_field
    @property
    def prefix(self) -> str:
        _, prefix = self._parse_oss_uri(self.uri)
        return prefix


@AssetFactory.register("oss")
class OSSAsset(
    IBastionObject,
    IAssetLike,
):
    """
    An OSS asset definition on Alibaba Cloud OSS storage, consists of multiple OSS objects.

    Args:
        name (str): Asset name.
        kind (AssetKind): Asset kind (parquet, csv, etc.).
        uri (str): OSS URI of the asset (e.g., oss://bucket-name/path/to/object).
        region (str): Alibaba Cloud region of the OSS bucket.
        endpoint (str | None): Optional custom OSS endpoint URL.
        partitions (list[str]): Partition column names.
        refs (list[BaseAssetRefModel]): Asset references.
        description (str | None): Optional description.
        owner (str | None): Optional owner identifier.
        metadata (dict[str, Any]): Arbitrary metadata.
        tags (dict[str, str]): Tag key-value pairs.

    Methods:
        inspect() -> list[OSSAssetRef]: Discover and return a list of OSS object references for the asset.

    Example:
        >>> oss_asset = OSSAsset(
        ...     name="my_oss_asset",
        ...     kind=AssetKind.PARQUET,
        ...     uri="oss://my-bucket/path/to/data",
        ...     region="oss-cn-hangzhou",
        ... )
        >>> refs = oss_asset.inspect()
        >>> for ref in refs:
        ...     print(ref.uri, ref.size, ref.modified_at)

    """

    _domain_class: type[OSSAssetModel] = OSSAssetModel

    def _parse_partition(
        self,
        key: str,
    ) -> dict[str, str]:
        if not self.domain.partitions:
            return {}
        result: dict[str, str] = {}
        relative_key = key[len(self.domain.prefix) :].lstrip("/")
        parts = relative_key.split("/")
        for part in parts:
            if "=" not in part:
                continue
            _key, _value = part.split("=", 1)
            if _key in self.domain.partitions:
                result[_key] = _value
        return result

    def inspect(
        self,
        adaptor: IOSSAdaptorLike | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[OSSAssetRef]:
        _adaptor: IOSSAdaptorLike = adaptor or OSSAdaptor(
            region=self.domain.region,
            endpoint=self.domain.endpoint,
        )
        refs: list[OSSAssetRef] = []
        _all_files = _adaptor.list_objects(
            bucket=self.domain.bucket,
            prefix=self.domain.prefix,
            since=since,
            until=until,
            limit=limit,
        )
        _bucket: str = self.domain.bucket
        _region: str | None = self.domain.region
        for file in _all_files:
            _key: str = file.key
            _uri: str = f"oss://{_bucket}/{_key}"
            _size: int = file.size
            _partitions: dict[str, str] = self._parse_partition(_key)
            _dt: datetime = file.last_modified
            _modified_at: datetime = _dt.astimezone(UTC)
            ref = OSSAssetRef(
                uri=_uri,
                size=_size,
                modified_at=_modified_at,
                partitions=_partitions,
                region=_region,
            )
            refs.append(ref)

        self.domain.refs = refs
        return refs
