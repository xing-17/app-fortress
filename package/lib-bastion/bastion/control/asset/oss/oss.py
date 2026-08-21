from __future__ import annotations

from datetime import datetime, UTC
import logging
from urllib.parse import urlparse

from pydantic import Field, computed_field

from bastion._internal.object import IBastionObject
from bastion.control.asset.base.base import IAssetLike
from bastion.domain.platform import Platform
from bastion.control.asset.base.factory import AssetFactory
from bastion.domain.asset import BaseAssetModel
from bastion.domain.assetref import BaseAssetRefModel


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
            import alibabacloud_oss_v2 as ossv2

            _client: ossv2.Client = client
            _paginator = _client.list_objects_v2_paginator()
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
                if obj.last_modified is not None:
                    _modified_at: datetime | None = datetime.fromtimestamp(
                        timestamp=obj.last_modified,
                        tz=UTC,
                    )
                else:
                    _modified_at = None
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
