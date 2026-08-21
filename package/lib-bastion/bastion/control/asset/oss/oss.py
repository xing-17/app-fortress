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

logger = logging.getLogger(__name__)


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

    def _oss_create_client(self) -> object:
        try:
            import alibabacloud_oss_v2 as ossv2

            _cred = ossv2.credentials.EnvironmentVariableCredentialsProvider()
            _cfg = ossv2.config.load_default()
            _cfg.credentials_provider = _cred
            _cfg.region = self.domain.region
            if self.domain.endpoint:
                _cfg.endpoint = self.domain.endpoint
            _client = ossv2.Client(_cfg)
            return _client
        except ImportError as e:
            raise ImportError(f"alibabacloud_oss_v2 is required for OSSAsset: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to create OSS bucket client: {e}") from e

    def _oss_get_object_paginator(
        self,
        client: object,
    ) -> object:
        try:
            _paginator = client.list_objects_v2_paginator()
            return _paginator
        except ImportError as e:
            raise ImportError(f"alibabacloud_oss_v2 is required for OSSAsset: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to create OSS object paginator: {e}") from e

    def _oss_build_request(self) -> object:
        try:
            import alibabacloud_oss_v2 as ossv2

            _request = ossv2.ListObjectsV2Request(
                bucket=self.domain.bucket,
                prefix=self.domain.prefix,
            )
            return _request
        except ImportError as e:
            raise ImportError(f"alibabacloud_oss_v2 is required for OSSAsset: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to build OSS request: {e}") from e

    def inspect(
        self,
        client: object | None = None,
    ) -> list[OSSAssetRef]:
        _client: object = client or self._oss_create_client()
        _paginator: object = self._oss_get_object_paginator(_client)
        _request: object = self._oss_build_request()
        refs: list[OSSAssetRef] = []
        for _ite in _paginator.iter_page(_request):
            for obj in _ite.contents:
                _bucket_name: str = self.domain.bucket
                _key: str = obj.key
                _region: str | None = self.domain.region
                _uri: str = f"oss://{_bucket_name}/{_key}"
                _size: int = obj.size
                _partitions: dict[str, str] = self._parse_partition(_key)
                _dt: datetime = obj.last_modified
                _modified_at: datetime = _dt.astimezone(UTC)
                ref = OSSAssetRef(
                    uri=_uri,
                    size=_size,
                    modified_at=_modified_at,
                    partitions=_partitions,
                    region=_region,
                )
                refs.append(ref)

        logger.info(f"Found {len(refs)} objects for asset '{self.domain.name}'")
        self.domain.refs = refs
        return refs
