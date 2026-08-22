from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from bastion.control.asset.base.base import IAdaptorLike


@runtime_checkable
class IOSSAdaptorLike(IAdaptorLike, Protocol):
    """
    Protocol an adaptor that can read files from OSS.

    Methods:
        list_objects: List files in a directory matching a pattern, with optional time slicing and limit

    """

    def list_objects(
        self,
        bucket: str,
        prefix: str,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[object]: ...


class OSSAdaptor(IOSSAdaptorLike):
    """
    An adaptor that can read files from OSS.
    deps: alibabacloud_credential


    Methods:
        list_objects: List files in a directory matching a pattern, with optional time slicing and limit

    Dependencies:
        alibabacloud_oss_v2: Required for interacting with Alibaba Cloud OSS.

    """

    def __init__(
        self,
        region: str,
        endpoint: str | None = None,
        access_key_id: str | None = None,
        access_key_secret: str | None = None,
        **kwargs,
    ) -> None:
        self.region = region
        self.endpoint = endpoint
        self._creds = {
            "access_key_id": access_key_id,
            "access_key_secret": access_key_secret,
            **kwargs,
        }

    def _get_client(self):
        try:
            import alibabacloud_oss_v2 as ossv2
            from alibabacloud_oss_v2.credentials import (
                EnvironmentVariableCredentialsProvider,
                StaticCredentialsProvider,
            )

            _args = {k: v for k, v in self._creds.items() if v is not None}
            if not _args:
                _provider = EnvironmentVariableCredentialsProvider()
            else:
                _provider = StaticCredentialsProvider(
                    access_key_id=self._creds.get("access_key_id"),
                    access_key_secret=self._creds.get("access_key_secret"),
                    security_token=self._creds.get("security_token"),
                )
            _cfg = ossv2.config.load_default()
            _cfg.credentials_provider = _provider
            _cfg.region = self.region
            if self.endpoint:
                _cfg.endpoint = self.endpoint
            _client = ossv2.Client(_cfg)
            return _client
        except ImportError as e:
            raise ImportError(f"alibabacloud_oss_v2 is required for OSSAdaptor: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to create OSS client: {e}") from e

    def _get_oss_paginator(self):
        _client = self._get_client()
        try:
            _paginator = _client.list_objects_v2_paginator()
            return _paginator
        except ImportError as e:
            raise ImportError(f"alibabacloud_oss_v2 is required for OSSAdaptor: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to create OSS paginator: {e}") from e

    def _get_oss_request(
        self,
        bucket: str,
        prefix: str,
    ) -> object:
        try:
            import alibabacloud_oss_v2 as ossv2

            _request = ossv2.ListObjectsV2Request(
                bucket=bucket,
                prefix=prefix,
            )
            return _request
        except ImportError as e:
            raise ImportError(f"alibabacloud_oss_v2 is required for OSSAdaptor: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to build OSS request: {e}") from e

    def _slice_by_time(
        self,
        files: list[object],
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[dict[str, str | int | datetime]]:
        if since is None and until is None:
            return files
        _filtered: list[object] = []
        for file in files:
            _modified_at: datetime | None = file.last_modified.as_timezone(UTC)
            if _modified_at is None:
                continue
            if since and _modified_at < since:
                continue
            if until and _modified_at > until:
                continue
            _filtered.append(file)
        return _filtered

    def _slice_by_limit(
        self,
        files: list[object],
        limit: int | None = None,
    ) -> list[dict]:
        if limit is None:
            return files
        if limit <= 0 or limit > len(files):
            return files
        return files[:limit]

    def list_objects(
        self,
        bucket: str,
        prefix: str,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[object]:
        _result: list[object] = []
        _paginator = self._get_oss_paginator()
        _request = self._get_oss_request(bucket=bucket, prefix=prefix)
        for _ite in _paginator.iter_page(_request):
            for obj in _ite.contents or []:
                _result.append(obj)
        _result = self._slice_by_time(_result, since=since, until=until)
        _result = self._slice_by_limit(_result, limit=limit)
        _result.sort(key=lambda x: x.last_modified, reverse=True)
        return _result
