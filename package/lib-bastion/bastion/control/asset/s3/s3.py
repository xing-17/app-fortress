from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urlparse

from pydantic import Field, computed_field

from bastion._internal.object import IBastionObject
from bastion.control.asset.base.base import IAssetLike
from bastion.control.asset.base.factory import AssetFactory
from bastion.domain.asset import BaseAssetModel
from bastion.domain.assetref import BaseAssetRefModel
from bastion.domain.platform import Platform

logger = logging.getLogger(__name__)


class _S3ObjectMixin:
    def _parse_s3_uri(self, uri: str) -> tuple[str, str]:
        parsed = urlparse(uri)
        if parsed.scheme != "s3":
            raise ValueError(f"Invalid S3 URI: {uri}")
        bucket = parsed.netloc
        prefix = parsed.path.lstrip("/")
        return bucket, prefix


class S3AssetRef(
    BaseAssetRefModel,
    _S3ObjectMixin,
):
    """
    A S3 object reference in AWS S3 storage.

    Attributes:
        uri: S3 URI of the object (e.g., s3://bucket-name/path/to/object)
        size: Size of the object in bytes
        modified_at: Last modified timestamp of the object
        partitions: Partition values extracted from the S3 key (if applicable)
        region: AWS region of the S3 bucket
        storage_class: Storage class of the S3 object (e.g., STANDARD, GLACIER)
        etag: ETag of the S3 object

    """

    region: str | None = Field(
        default=None,
        description="Region of the S3 bucket",
    )
    storage_class: str | None = Field(
        default=None,
        description="Storage class of the S3 object",
    )
    etag: str | None = Field(
        default=None,
        description="ETag of the S3 object",
    )

    @computed_field
    @property
    def bucket(self) -> str:
        bucket, _ = self._parse_s3_uri(self.uri)
        return bucket

    @computed_field
    @property
    def prefix(self) -> str:
        _, prefix = self._parse_s3_uri(self.uri)
        return prefix


class S3AssetModel(
    BaseAssetModel,
    _S3ObjectMixin,
):
    """
    Domain model for S3 assets.

    Attributes:
        name (str): Asset name.
        kind (AssetKind): Asset kind (parquet, csv, etc.).
        uri (str): S3 URI of the asset (e.g., s3://bucket-name/path/to/object).
        region (str | None): AWS region of the S3 bucket.
        partitions (list[str]): Partition column names.
        refs (list[BaseAssetRefModel]): Asset references.
        description (str | None): Optional description.
        owner (str | None): Optional owner identifier.
        metadata (dict[str, Any]): Arbitrary metadata.
        tags (dict[str, str]): Tag key-value pairs.
        bucket (str): Computed from uri - the S3 bucket name.
        prefix (str): Computed from uri - the S3 object key/path.

    """

    platform: Platform = Platform.S3
    uri: str = Field(
        ...,
        description="S3 URI of the asset (e.g., s3://bucket-name/path/to/object)",
    )
    region: str | None = Field(
        default=None,
        description="Region of the S3 bucket",
    )

    @computed_field
    @property
    def bucket(self) -> str:
        bucket, _ = self._parse_s3_uri(self.uri)
        return bucket

    @computed_field
    @property
    def prefix(self) -> str:
        _, prefix = self._parse_s3_uri(self.uri)
        return prefix


@AssetFactory.register("s3")
class S3Asset(
    IBastionObject,
    IAssetLike,
):
    """
    A S3 asset definition on AWS S3 storage, consists of multiple S3 objects.

    Args:
        name (str): Asset name.
        kind (AssetKind): Asset kind (parquet, csv, etc.).
        uri (str): S3 URI of the asset (e.g., s3://bucket-name/path/to/object).
        region (str | None): AWS region of the S3 bucket.
        partitions (list[str]): Partition column names.
        refs (list[BaseAssetRefModel]): Asset references.
        description (str | None): Optional description.
        owner (str | None): Optional owner identifier.
        metadata (dict[str, Any]): Arbitrary metadata.
        tags (dict[str, str]): Tag key-value pairs.
        bucket (str): Computed from uri - the S3 bucket name.
        prefix (str): Computed from uri - the S3 object key/path.

    Methods:
        inspect() -> list[S3AssetRef]: Discover S3 objects and return their references.

    Example:
        >>> s3_asset = S3Asset(
        ...     name="my_s3_asset",
        ...     kind=AssetKind.PARQUET,
        ...     uri="s3://my-bucket/path/to/data",
        ...     region="us-west-2",
        ...     partitions=["year", "month"],
        ... )
        >>> refs = s3_asset.inspect()
        >>> for ref in refs:
        ...     print(ref.uri, ref.size, ref.modified_at)

    """

    _domain_class: type[S3AssetModel] = S3AssetModel

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

    def _s3_create_client(self) -> object:
        try:
            import boto3

            return boto3.client(
                "s3",
                region_name=self.domain.region,
            )
        except ImportError as e:
            raise ImportError(f"boto3 is required for S3Asset: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to create S3 client: {e}") from e

    def _s3_get_page_iterator(
        self,
        client: object,
    ) -> object:
        """Get a paginator for listing S3 objects."""
        try:
            paginator = client.get_paginator("list_objects_v2")
            return paginator.paginate(
                Bucket=self.domain.bucket,
                Prefix=self.domain.prefix,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get S3 paginator: {e}") from e

    def inspect(
        self,
        client: object | None = None,
    ) -> list[S3AssetRef]:
        # Ensure boto3 is available
        _client = client or self._s3_create_client()
        _iterator = self._s3_get_page_iterator(_client)
        refs: list[S3AssetRef] = []
        for _ite in _iterator:
            for obj in _ite.get("Contents", []):
                _bucket: str = self.domain.bucket
                _key: str = obj["Key"]
                _region: str | None = self.domain.region
                _uri: str = f"s3://{_bucket}/{_key}"
                _size: int = obj.get("Size", 0)
                _modified_at: datetime | None = obj.get("LastModified")
                _etag: str | None = obj.get("ETag")
                _storage_class: str | None = obj.get("StorageClass")
                _partitions: dict[str, str] = self._parse_partition(_key)
                ref = S3AssetRef(
                    uri=_uri,
                    size=_size,
                    modified_at=_modified_at,
                    etag=_etag,
                    storage_class=_storage_class,
                    partitions=_partitions,
                    region=_region,
                )
                refs.append(ref)

        logger.info(f"Found {len(refs)} objects for asset '{self.domain.name}'")
        self.domain.refs = refs
        return refs
