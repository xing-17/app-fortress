from __future__ import annotations

import io
import threading
from collections import OrderedDict, deque
from datetime import datetime
from fnmatch import fnmatchcase
from typing import Any

from alibabacloud_oss_v2.client import Client as OSSTeaClient
from alibabacloud_oss_v2.config import load_default
from alibabacloud_oss_v2.credentials import Credentials, CredentialsProviderFunc
from alibabacloud_oss_v2.exceptions import OperationError, ServiceError
from alibabacloud_oss_v2.models import (
    GetObjectRequest,
    GetObjectResult,
    HeadObjectRequest,
    HeadObjectResult,
    ListObjectsV2Request,
    PutObjectRequest,
)
from alibabacloud_oss_v2.paginator import ListObjectsV2Paginator

from app.internal.util.clock import IClock
from app.resource.identity.aliyun.aliyun import AliyunIdentity


class OSSClient:
    """
    Aliyun OSS Tea SDK 客户端,

    Args:
        bucket (str): OSS bucket 名称
        region (str): OSS bucket 区域
        identity (AliyunIdentity): 用于认证 OSS 的阿里云身份
        in_vpc (bool): 是否使用 VPC 内网 endpoint(默认 False)

    Attributes:
        client (OSSTeaClient): 懒加载并缓存的 Tea SDK 客户端实例，凭证按需实时获取以支持刷新。

    Methods:
        get_client(bucket, region, identity, in_vpc=False) -> OSSClient:
            按 (bucket, region, identity) 从进程级 LRU 缓存中获取或创建实例。
        write_bytes(key: str, data: bytes) -> None:
            将原始字节写入指定 key 的对象。
        read_bytes(key: str) -> bytes:
            从指定 key 的对象中读取原始字节；key 不存在时抛出 FileNotFoundError。
        list_objects(prefix, pattern=None, since=None, until=None, recursive=True) -> list[dict]:
            列出指定前缀下的对象元数据，分页获取所有结果，可按 glob 模式/修改时间过滤。
        list_folders(prefix, pattern=None, recursive=True) -> list[dict]:
            列出指定前缀下的“文件夹”（common prefix），recursive 控制是否递归子层级。
        get_object(key: str) -> dict:
            获取单个对象的元数据；key 不存在时抛出 FileNotFoundError。
        reset() -> None:
            清空进程级实例缓存(主要用于测试隔离)。

    """

    _cache: OrderedDict[tuple[str, str, str], "OSSClient"] = OrderedDict()
    _cache_lock = threading.RLock()
    _cache_max_size: int = 20

    @classmethod
    def get_client(
        cls,
        bucket: str,
        region: str,
        identity: AliyunIdentity,
        in_vpc: bool = False,
    ) -> "OSSClient":
        _key = (bucket, region, identity.sha256())
        with cls._cache_lock:
            _hit: OSSClient | None = cls._cache.get(_key)
            if _hit is not None:
                cls._cache.move_to_end(_key)
                return _hit

            # Cache miss, create a new client instance
            _instance: OSSClient = OSSClient(
                bucket=bucket,
                region=region,
                identity=identity,
                in_vpc=in_vpc,
            )
            cls._cache[_key] = _instance
            if len(cls._cache) > cls._cache_max_size:
                cls._cache.popitem(last=False)
            return _instance

    def __init__(
        self,
        bucket: str,
        region: str,
        identity: AliyunIdentity,
        in_vpc: bool = False,
    ) -> None:
        self.bucket: str = bucket
        self.region: str = region
        self.identity: AliyunIdentity = identity
        self.in_vpc: bool = in_vpc
        self.endpoint: str = self._resolve_endpoint()
        self._client: OSSTeaClient | None = None
        self._client_lock: threading.RLock = threading.RLock()

    def _resolve_endpoint(self) -> str:
        _ep: str = "-internal" if self.in_vpc else ""
        return f"oss-{self.region}{_ep}.aliyuncs.com"

    @property
    def client(self) -> OSSTeaClient:
        def get_credentials_wrapper():
            cred = self.identity.get_credential()
            return Credentials(
                access_key_id=cred.access_key_id,
                access_key_secret=cred.access_key_secret,
                security_token=cred.security_token,
            )

        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    _cfg = load_default()
                    _cfg.credentials_provider = CredentialsProviderFunc(func=get_credentials_wrapper)
                    _cfg.region = self.region
                    _cfg.endpoint = self.endpoint
                    self._client = OSSTeaClient(_cfg)
        return self._client

    def write_bytes(
        self,
        key: str,
        data: bytes,
    ) -> None:
        _request: PutObjectRequest = PutObjectRequest(
            bucket=self.bucket,
            key=key,
            body=io.BytesIO(data),
        )
        self.client.put_object(_request)

    def read_bytes(
        self,
        key: str,
    ) -> bytes:
        try:
            _request: GetObjectRequest = GetObjectRequest(
                bucket=self.bucket,
                key=key,
            )
            _response: GetObjectResult = self.client.get_object(_request)
            _result: bytes = _response.body.read()
        except OperationError as e:
            _cause = e.unwrap()
            if isinstance(_cause, ServiceError) and _cause.code == "NoSuchKey":
                raise FileNotFoundError(key) from e
            raise
        return _result

    def list_objects(
        self,
        prefix: str = "",
        pattern: str | None = None,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        _om_list: list[dict[str, Any]] = []
        _delimiter: str | None = None if recursive else "/"
        if since is not None and isinstance(since, datetime):
            _dt: datetime = IClock.from_datetime(since, timezone="UTC")
            since = _dt.timestamp()
        if until is not None and isinstance(until, datetime):
            _dt: datetime = IClock.from_datetime(until, timezone="UTC")
            until = _dt.timestamp()
        _paginater: ListObjectsV2Paginator = self.client.list_objects_v2_paginator()
        _request: ListObjectsV2Request = ListObjectsV2Request(
            bucket=self.bucket,
            prefix=prefix,
            delimiter=_delimiter,
            fetch_owner=True,
        )
        for _page in _paginater.iter_page(request=_request):
            for _content in _page.contents or []:
                _key: str = _content.key
                if pattern and not fnmatchcase(_key, pattern):
                    continue
                _lmdt: datetime = _content.last_modified
                _lmts: float = _lmdt.timestamp() if isinstance(_lmdt, datetime) else None
                if since is not None and _lmts is not None and _lmts < since:
                    continue
                if until is not None and _lmts is not None and _lmts > until:
                    continue
                _om: dict[str, Any] = {
                    "bucket": self.bucket,
                    "key": _key,
                    "etag": _content.etag,
                    "last_modified": _lmts,
                    "size": _content.size,
                    "storage_class": _content.storage_class,
                }
                _om_list.append(_om)
        _om_list: list[dict[str, Any]] = sorted(
            _om_list,
            key=lambda x: x["key"],
        )
        return _om_list

    def list_folders(
        self,
        prefix: str = "",
        pattern: str | None = None,
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        _fm_list: list[dict[str, Any]] = []
        _queue: deque[str] = deque([prefix])
        while _queue:
            _cur_prefix: str = _queue.popleft()
            _paginator = self.client.list_objects_v2_paginator()
            _request = ListObjectsV2Request(
                bucket=self.bucket,
                prefix=_cur_prefix,
                delimiter="/",
            )
            for _page in _paginator.iter_page(request=_request):
                for _cp in _page.common_prefixes or []:
                    if not pattern or fnmatchcase(_cp.prefix, pattern):
                        _fm: dict[str, Any] = {
                            "bucket": self.bucket,
                            "prefix": _cp.prefix,
                        }
                        _fm_list.append(_fm)
                    if recursive:
                        _queue.append(_cp.prefix)
        _fm_list: list[dict[str, Any]] = sorted(
            _fm_list,
            key=lambda x: x["prefix"],
        )
        return _fm_list

    def get_object(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        try:
            _request = HeadObjectRequest(
                bucket=self.bucket,
                key=key,
            )
            _response: HeadObjectResult = self.client.head_object(_request)
        except OperationError as e:
            _cause = e.unwrap()
            if isinstance(_cause, ServiceError) and _cause.code == "NoSuchKey":
                raise FileNotFoundError(key) from e
            raise
        _lmdt: datetime | None = _response.last_modified
        _lmts: float | None = _lmdt.timestamp() if isinstance(_lmdt, datetime) else None
        return {
            "bucket": self.bucket,
            "key": key,
            "etag": _response.etag,
            "last_modified": _lmts,
            "size": _response.content_length,
            "storage_class": _response.storage_class,
        }

    @classmethod
    def reset(cls) -> None:
        with cls._cache_lock:
            cls._cache = OrderedDict()
