from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from bastion.control.asset.base.base import IAdaptorLike


@runtime_checkable
class IS3AdaptorLike(IAdaptorLike, Protocol):
    """
    Protocol an adaptor that can read files from S3.

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
    ) -> list[Path]: ...


class S3Adaptor(IS3AdaptorLike):
    """
    An adaptor that can read files from S3.

    Args:
        access_key_id: AWS access key ID (optional)
        access_key_secret: AWS secret access key (optional)
        session_token: AWS session token (optional)
        account_id: AWS account ID (optional)
        region: AWS region (optional)
        profile: AWS profile name (optional)
        kwargs: Additional keyword arguments for boto3 session (optional)

    Methods:
        list_objects: List files in an S3 bucket under a prefix, with optional time slicing and limit

    """

    def __init__(
        self,
        access_key_id: str | None = None,
        access_key_secret: str | None = None,
        session_token: str | None = None,
        account_id: str | None = None,
        region: str | None = None,
        profile: str | None = None,
        **kwargs,
    ) -> None:
        self._creds = {
            "aws_access_key_id": access_key_id,
            "aws_secret_access_key": access_key_secret,
            "aws_session_token": session_token,
            "region_name": region,
            "profile_name": profile,
            "aws_account_id": account_id,
            **kwargs,
        }

    def _get_client(self):
        try:
            import boto3

            _args = {k: v for k, v in self._creds.items() if v is not None}
            session = boto3.session.Session(**_args)
            return session.client("s3")
        except ImportError as e:
            raise ImportError(f"boto3 is required for S3Adaptor: {e}") from e

    def _slice_by_time(
        self,
        files: list[dict[str, str | int | datetime]],
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[dict[str, str | int | datetime]]:
        if since is None and until is None:
            return files
        _filtered: list[dict[str, str | int | datetime]] = []
        for file in files:
            _modified_at: datetime | None = file.get("LastModified")
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
        files: list[dict],
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
    ) -> list[dict[str, str | int | datetime]]:
        _result: list[dict[str, str | int | datetime]] = []
        _client = self._get_client()
        if not hasattr(_client, "get_paginator"):
            raise RuntimeError(f"'{type(_client)}' does not support pagination.")
        _paginator = _client.get_paginator("list_objects_v2")
        _iterator = _paginator.paginate(
            Bucket=bucket,
            Prefix=prefix,
        )
        for _page in _iterator:
            for obj in _page.get("Contents", []):
                _result.append(obj)
        _result = self._slice_by_time(_result, since=since, until=until)
        _result = self._slice_by_limit(_result, limit=limit)
        _result.sort(key=lambda x: x.get("LastModified"), reverse=True)
        return _result
