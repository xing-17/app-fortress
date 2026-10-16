from __future__ import annotations

import io
import threading
from unittest.mock import MagicMock

import pytest
from alibabacloud_fc20230330.models import InvokeFunctionResponse

from app.resource._client.fc import client as fc_client_module
from app.resource._client.fc.client import FCClient
from app.resource.identity.aliyun.identity import AliyunIdentity


def _make_identity(name: str = "my-identity") -> AliyunIdentity:
    return AliyunIdentity(name=name)


def _response(
    body: bytes = b"",
    headers: dict[str, str] | None = None,
    status_code: int = 200,
) -> InvokeFunctionResponse:
    return InvokeFunctionResponse(
        headers=headers or {},
        status_code=status_code,
        body=io.BytesIO(body),
    )


def _client_with(response: InvokeFunctionResponse) -> tuple[FCClient, MagicMock]:
    _client = FCClient(region="cn-hangzhou", identity=_make_identity())
    _tea = MagicMock()
    _tea.invoke_function_with_options.return_value = response
    _client._client = _tea
    return _client, _tea


@pytest.fixture(autouse=True)
def _reset_client_cache():
    # FCClient._cache holds process-wide singleton state; isolate tests from each other.
    FCClient.reset()
    yield
    FCClient.reset()


class TestFCClientEndpoint:
    def test_public_endpoint(self):
        assert FCClient(region="cn-hangzhou", identity=_make_identity()).endpoint == "fcv3.cn-hangzhou.aliyuncs.com"

    def test_vpc_endpoint(self):
        _c = FCClient(region="cn-hangzhou", identity=_make_identity(), in_vpc=True)
        assert _c.endpoint == "fcv3.cn-hangzhou-internal.aliyuncs.com"


class TestFCClientGetClient:
    def test_same_args_return_same_instance(self):
        _identity = _make_identity()
        assert FCClient.get_client("cn-hangzhou", _identity) is FCClient.get_client("cn-hangzhou", _identity)

    def test_different_region_returns_different_instance(self):
        _identity = _make_identity()
        assert FCClient.get_client("cn-hangzhou", _identity) is not FCClient.get_client("cn-beijing", _identity)

    def test_different_vpc_returns_different_instance(self):
        _identity = _make_identity()
        assert FCClient.get_client("cn-hangzhou", _identity) is not FCClient.get_client(
            "cn-hangzhou", _identity, in_vpc=True
        )

    def test_cache_evicts_oldest_when_full(self, monkeypatch):
        monkeypatch.setattr(FCClient, "_cache_max_size", 2)
        _identity = _make_identity()
        _first = FCClient.get_client("r1", _identity)
        FCClient.get_client("r2", _identity)
        FCClient.get_client("r3", _identity)
        assert FCClient.get_client("r1", _identity) is not _first

    def test_reset_clears_cache(self):
        _identity = _make_identity()
        _first = FCClient.get_client("cn-hangzhou", _identity)
        FCClient.reset()
        assert FCClient.get_client("cn-hangzhou", _identity) is not _first


class TestFCClientLazyClient:
    def test_client_is_built_once_with_endpoint_and_credential(self, monkeypatch):
        _configs: list = []
        _credential = object()
        monkeypatch.setattr(AliyunIdentity, "get_client", lambda self: _credential)

        def _fake_tea_client(cfg):
            _configs.append(cfg)
            return MagicMock()

        monkeypatch.setattr(fc_client_module, "FCTeaClient", _fake_tea_client)
        _c = FCClient(region="cn-hangzhou", identity=_make_identity())
        assert _c.client is _c.client
        assert len(_configs) == 1
        assert _configs[0].endpoint == "fcv3.cn-hangzhou.aliyuncs.com"
        assert _configs[0].region_id == "cn-hangzhou"
        assert _configs[0].credential is _credential

    def test_concurrent_access_builds_single_client(self, monkeypatch):
        _count = 0
        monkeypatch.setattr(AliyunIdentity, "get_client", lambda self: object())

        def _fake_tea_client(cfg):
            nonlocal _count
            _count += 1
            return MagicMock()

        monkeypatch.setattr(fc_client_module, "FCTeaClient", _fake_tea_client)
        _c = FCClient(region="cn-hangzhou", identity=_make_identity())
        _threads = [threading.Thread(target=lambda: _c.client) for _ in range(8)]
        for _t in _threads:
            _t.start()
        for _t in _threads:
            _t.join()
        assert _count == 1


class TestFCClientInvoke:
    def test_returns_parsed_body_and_request_id(self):
        _client, _tea = _client_with(_response(b'{"ok": true}', {"X-Fc-Request-Id": "req-1"}))
        _result = _client.invoke("fn", b"{}")
        assert _result == {"request_id": "req-1", "status_code": 200, "body": {"ok": True}, "error": None}

    def test_sets_sync_header_and_payload(self):
        _client, _tea = _client_with(_response())
        _client.invoke("fn", b'{"a": 1}', qualifier="prod")
        _kwargs = _tea.invoke_function_with_options.call_args.kwargs
        assert _kwargs["function_name"] == "fn"
        assert _kwargs["request"].qualifier == "prod"
        assert _kwargs["request"].body.read() == b'{"a": 1}'
        assert _kwargs["headers"].x_fc_invocation_type == "Sync"

    def test_timeout_is_passed_as_read_timeout_milliseconds(self):
        _client, _tea = _client_with(_response())
        _client.invoke("fn", b"{}", timeout_seconds=1.5)
        assert _tea.invoke_function_with_options.call_args.kwargs["runtime"].read_timeout == 1500

    def test_error_message_header_is_returned(self):
        _client, _ = _client_with(_response(b"{}", {"X-Fc-Error-Message": "boom"}))
        assert _client.invoke("fn", b"{}")["error"] == "boom"

    @pytest.mark.parametrize("body", [b"", b"not json"])
    def test_empty_or_invalid_body_is_empty_dict(self, body):
        _client, _ = _client_with(_response(body))
        assert _client.invoke("fn", b"{}")["body"] == {}

    def test_missing_body_is_empty_dict(self):
        _resp = InvokeFunctionResponse(headers={}, status_code=200, body=None)
        _client, _ = _client_with(_resp)
        assert _client.invoke("fn", b"{}")["body"] == {}

    def test_sdk_exceptions_propagate(self):
        _client, _tea = _client_with(_response())
        _tea.invoke_function_with_options.side_effect = ConnectionError("down")
        with pytest.raises(ConnectionError):
            _client.invoke("fn", b"{}")
