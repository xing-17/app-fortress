from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from app.service.mcphost.service.service import McpHostService
from app.setting.service import McpHostServiceSetting

from .fakes import FakeNodeClient

_BASE = "http://127.0.0.1:8801"
_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}


def _rpc(response) -> dict:
    # The transport answers a call as JSON or as one server-sent event
    if response.headers["content-type"].startswith("application/json"):
        return response.json()
    for _line in response.text.splitlines():
        if _line.startswith("data:"):
            return json.loads(_line[len("data:") :])
    raise AssertionError(response.text)


@pytest.fixture
def fake():
    return FakeNodeClient()


@pytest.fixture
def web(log, fake, user_auth):
    _setting = McpHostServiceSetting(nodes=[{"name": "centre", "endpoint": "http://centre:8800", "token": "t0ken"}])
    _service = McpHostService(_setting, client=fake, auth=user_auth)
    _service.start()
    with TestClient(_service.asgi_app(), base_url=_BASE) as _client:
        yield _client
    _service.stop()


def _bearer(auth, name):
    return {"Authorization": f"Bearer {auth.token(name)}"}


def _open_session(web, headers) -> dict:
    _res = web.post("/mcp", json=_INITIALIZE, headers={**_HEADERS, **headers})
    assert _res.status_code == 200, _res.text
    _session = {**_HEADERS, **headers, "mcp-session-id": _res.headers["mcp-session-id"]}
    web.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=_session)
    return _session


def _call(web, session, tool, arguments) -> dict:
    _body = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    return _rpc(web.post("/mcp", json=_body, headers=session))


class TestBearerAuth:
    @pytest.mark.parametrize(
        "headers",
        [
            {},
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer " + "0" * 64},
            {"Authorization": "Basic abc"},
        ],
    )
    def test_requests_without_a_valid_token_get_401(self, web, headers):
        _res = web.post("/mcp", json=_INITIALIZE, headers={**_HEADERS, **headers})
        assert _res.status_code == 401
        assert _res.json() == {"error": "unauthorized"}

    def test_a_revoked_token_gets_401(self, web, user_auth):
        _state = user_auth._state
        _token = user_auth._mac(_state.masterkey, _state.entries["gone"])
        _res = web.post("/mcp", json=_INITIALIZE, headers={**_HEADERS, "Authorization": f"Bearer {_token}"})
        assert _res.status_code == 401

    def test_the_node_token_is_not_a_user_token(self, web, node_auth):
        _res = web.post("/mcp", json=_INITIALIZE, headers={**_HEADERS, **_bearer(node_auth, "mcphost")})
        assert _res.status_code == 401

    def test_a_user_token_cannot_name_another_caller(self, web, user_auth):
        _headers = {**_bearer(user_auth, "phone"), "X-Fortress-Caller": "someone"}
        assert web.post("/mcp", json=_INITIALIZE, headers={**_HEADERS, **_headers}).status_code == 401

    def test_a_valid_token_opens_a_session(self, web, user_auth):
        _res = web.post("/mcp", json=_INITIALIZE, headers={**_HEADERS, **_bearer(user_auth, "phone")})
        assert _res.status_code == 200

    def test_nothing_is_public(self, web):
        assert web.get("/health").status_code == 401


class TestCaller:
    def test_the_user_is_passed_to_the_node(self, web, fake, user_auth):
        _session = _open_session(web, _bearer(user_auth, "phone"))
        _res = _call(web, _session, "query", {"sql": "SELECT 1"})
        assert "error" not in _res
        assert fake.callers == ["phone"]

    def test_the_user_is_in_the_call_trace(self, web, user_auth, log):
        _session = _open_session(web, _bearer(user_auth, "phone"))
        _call(web, _session, "list_datasets", {})
        _meta = log.info.call_args.kwargs["metadata"]
        assert _meta["caller"] == "phone"

    def test_the_token_is_not_logged(self, web, user_auth, log):
        _token = user_auth.token("phone")
        _session = _open_session(web, _bearer(user_auth, "phone"))
        _call(web, _session, "query", {"sql": "SELECT 1"})
        _logged = " ".join(str(c) for c in log.method_calls)
        assert _token not in _logged
