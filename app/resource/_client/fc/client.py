from __future__ import annotations

import io
import json
import threading
from collections import OrderedDict
from typing import Any

from alibabacloud_fc20230330.client import Client as FCTeaClient
from alibabacloud_fc20230330.models import (
    InvokeFunctionHeaders,
    InvokeFunctionRequest,
    InvokeFunctionResponse,
)
from alibabacloud_tea_openapi.utils_models import Config as FCTeaConfig
from darabonba.runtime import RuntimeOptions

from app.resource.identity.aliyun import AliyunIdentity


class FCClient:
    """
    Aliyun FC 3.0 Tea SDK 客户端。

    Attributes:
    ----------
        client (FCTeaClient):
            懒加载并缓存的 Tea SDK 客户端实例，凭证由 CredentialClient 自行刷新

    Args:
    ----------
        region (str):
            FC 函数所在区域
        identity (AliyunIdentity):
            用于认证 FC 的阿里云身份
        in_vpc (bool):
            是否使用 VPC 内网 endpoint，默认 False

    Methods:
    ----------
        get_client(region, identity, in_vpc=False) -> FCClient:
            按 (region, in_vpc, identity) 从进程级 LRU 缓存中获取或创建实例。
        invoke(function_name, payload, qualifier="LATEST", timeout_seconds=None) -> dict[str, Any]:
            调用函数；同步调用在函数抛错时抛出 RuntimeError，异步调用只返回受理结果，task_id 仅异步调用使用。
        reset() -> None:
            清空进程级实例缓存(主要用于测试隔离)。

    Example:
    ----------
        >>> identity = AliyunIdentity.default()
        >>> client = FCClient.get_client(region="cn-hangzhou", identity=identity)
        >>> client.invoke("my-function", b'{"a": 1}')["body"]

    """

    _cache: OrderedDict[tuple[str, bool, str], "FCClient"] = OrderedDict()
    _cache_lock = threading.RLock()
    _cache_max_size: int = 20

    @classmethod
    def get_client(
        cls,
        region: str,
        identity: AliyunIdentity,
        in_vpc: bool = False,
    ) -> "FCClient":
        _key = (region, in_vpc, identity.sha256())
        with cls._cache_lock:
            _hit: FCClient | None = cls._cache.get(_key)
            if _hit is not None:
                cls._cache.move_to_end(_key)
                return _hit

            # 缓存未命中，创建新的客户端实例
            _instance: FCClient = FCClient(
                region=region,
                identity=identity,
                in_vpc=in_vpc,
            )
            cls._cache[_key] = _instance
            if len(cls._cache) > cls._cache_max_size:
                cls._cache.popitem(last=False)
            return _instance

    @classmethod
    def reset(cls) -> None:
        with cls._cache_lock:
            cls._cache.clear()

    def __init__(
        self,
        region: str,
        identity: AliyunIdentity,
        in_vpc: bool = False,
    ) -> None:
        self.region: str = region
        self.identity: AliyunIdentity = identity
        self.in_vpc: bool = in_vpc
        self.endpoint: str = self._resolve_endpoint()
        self._client: FCTeaClient | None = None
        self._client_lock: threading.RLock = threading.RLock()

    def _resolve_endpoint(self) -> str:
        if self.in_vpc:
            _ep: str = "-internal"
        else:
            _ep: str = ""
        return f"fcv3.{self.region}{_ep}.aliyuncs.com"

    @property
    def client(self) -> FCTeaClient:
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    _cfg = FCTeaConfig(
                        credential=self.identity.get_client(),
                        endpoint=self.endpoint,
                        region_id=self.region,
                    )
                    self._client = FCTeaClient(_cfg)
        return self._client

    def invoke(
        self,
        function_name: str,
        payload: bytes,
        qualifier: str = "LATEST",
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        _name: str = function_name
        _runtime: RuntimeOptions = RuntimeOptions()
        if timeout_seconds is not None:
            _runtime.read_timeout = int(timeout_seconds * 1000)
        _res: InvokeFunctionResponse = self.client.invoke_function_with_options(
            function_name=_name,
            request=InvokeFunctionRequest(
                body=io.BytesIO(payload),
                qualifier=qualifier,
            ),
            headers=InvokeFunctionHeaders(
                x_fc_invocation_type="Sync",
            ),
            runtime=_runtime,
        )

        # normalize response headers
        _headers: dict[str, str] = {}
        for k, v in (_res.headers or {}).items():
            _headers[str(k).lower()] = v

        # Read the response body if it exists
        if _res.body is not None:
            _body: bytes = _res.body.read()
        else:
            _body: bytes = b"{}"
        try:
            _content: dict = json.loads(_body) if _body else {}
        except json.JSONDecodeError:
            _content = {}

        _status_code: int = _res.status_code
        _request_id: str | None = _headers.get("x-fc-request-id")
        _error: str | None = _headers.get("x-fc-error-message")
        return {
            "request_id": _request_id,
            "status_code": _status_code,
            "body": _content,
            "error": _error,
        }
