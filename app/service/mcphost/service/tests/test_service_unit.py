from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette

from app.internal.constant.servicestate import ServiceState
from app.service.mcphost.service.service import McpHostService
from app.service.node.client.httpnode import HttpNodeClient
from app.service.node.service.errors import NodeUnauthorizedError, NodeUnavailableError
from app.setting.service import McpHostServiceSetting, NodeServiceSetting

from .fakes import FakeNodeClient


def _setting(**nodes):
    _names = nodes or {"centre": 1}
    _nodes = [{"name": n, "endpoint": f"http://{n}:8800", "token": "t0ken"} for n in _names]
    return McpHostServiceSetting(nodes=_nodes)


@pytest.fixture
def fake():
    return FakeNodeClient()


@pytest.fixture
def service(log, fake, user_auth):
    _service = McpHostService(_setting(), clients={"centre": fake}, auth=user_auth)
    yield _service
    _service.stop()


class TestConstruction:
    def test_requires_an_mcphost_setting(self, log):
        with pytest.raises(ValueError, match="requires a mcphost setting"):
            McpHostService(NodeServiceSetting())

    def test_serves_every_node_by_default(self, log):
        _service = McpHostService(_setting(a=1, b=1))
        assert [n.name for n in _service.nodes] == ["a", "b"]

    def test_selects_a_node_by_name(self, log):
        _service = McpHostService(_setting(a=1, b=1), node="b")
        assert [n.name for n in _service.nodes] == ["b"]

    def test_unknown_node_lists_the_known_ones(self, log):
        with pytest.raises(ValueError, match=r"'nope'.*\['a', 'b'\]"):
            McpHostService(_setting(a=1, b=1), node="nope")

    def test_clients_of_unknown_nodes_are_refused(self, log):
        with pytest.raises(ValueError, match=r"\['nope'\]"):
            McpHostService(_setting(), clients={"nope": FakeNodeClient()})


class TestStart:
    def test_start_checks_the_node_and_the_token(self, service, fake):
        service.start()
        assert service.is_running
        assert [c[0] for c in fake.calls[:2]] == ["health", "list_sources"]

    def test_node_that_is_not_running_fails_the_start(self, service, fake):
        fake.node_health = {"state": "stopped", "is_running": False}
        with pytest.raises(RuntimeError, match="not running"):
            service.start()
        assert service.state == ServiceState.FAILED

    def test_unreachable_node_fails_the_start(self, service, fake):
        fake.raises = NodeUnavailableError("unreachable")
        with pytest.raises(NodeUnavailableError):
            service.start()
        assert service.state == ServiceState.FAILED

    def test_rejected_token_fails_the_start(self, service, fake, monkeypatch):
        monkeypatch.setattr(fake, "list_sources", lambda: (_ for _ in ()).throw(NodeUnauthorizedError("rejected")))
        with pytest.raises(NodeUnauthorizedError):
            service.start()
        assert service.state == ServiceState.FAILED

    def test_node_without_a_token_fails_the_start(self, log):
        _setting_ = McpHostServiceSetting(nodes=[{"name": "centre", "endpoint": "http://x:8800"}])
        _service = McpHostService(_setting_)
        with pytest.raises(ValueError, match="no token"):
            _service.start()
        assert _service.state == ServiceState.FAILED

    def test_one_node_down_does_not_fail_the_start(self, log, user_auth):
        _up, _down = FakeNodeClient(), FakeNodeClient()
        _down.raises = NodeUnavailableError("unreachable")
        _service = McpHostService(_setting(a=1, b=1), clients={"a": _up, "b": _down}, auth=user_auth)
        _service.start()
        assert _service.is_running
        _service.stop()

    def test_every_node_down_fails_the_start(self, log):
        _a, _b = FakeNodeClient(), FakeNodeClient()
        _a.raises = NodeUnavailableError("a is gone")
        _b.raises = NodeUnavailableError("b is gone")
        _service = McpHostService(_setting(a=1, b=1), clients={"a": _a, "b": _b})
        with pytest.raises(NodeUnavailableError, match="a is gone"):
            _service.start()
        assert _service.state == ServiceState.FAILED


class TestClientOwnership:
    def test_a_given_client_is_not_closed(self, service, fake):
        service.start()
        service.stop()
        assert fake.closed is False

    def test_its_own_client_is_closed_on_stop(self, log, monkeypatch):
        _closed = []
        _fake = FakeNodeClient()
        _fake.close = lambda: _closed.append(True)
        monkeypatch.setattr(HttpNodeClient, "from_setting", classmethod(lambda cls, setting: _fake))
        _service = McpHostService(_setting())
        _service.start()
        _service.stop()
        assert _closed == [True]

    def test_its_own_client_is_closed_when_the_start_fails(self, log, monkeypatch):
        _closed = []
        _fake = FakeNodeClient()
        _fake.node_health = {"state": "stopped", "is_running": False}
        _fake.close = lambda: _closed.append(True)
        monkeypatch.setattr(HttpNodeClient, "from_setting", classmethod(lambda cls, setting: _fake))
        _service = McpHostService(_setting())
        with pytest.raises(RuntimeError):
            _service.start()
        assert _closed == [True]

    def test_builds_an_http_client_from_the_node_setting(self, log, monkeypatch):
        _seen = []

        def _from_setting(cls, setting):
            _seen.append(setting)
            return FakeNodeClient()

        monkeypatch.setattr(HttpNodeClient, "from_setting", classmethod(_from_setting))
        McpHostService(_setting(a=1, b=1), node="b").start()
        assert [s.name for s in _seen] == ["b"]
        assert _seen[0].token.get_secret_value() == "t0ken"


class TestAsgiApp:
    def test_requires_a_running_service(self, service):
        with pytest.raises(RuntimeError, match="not running"):
            service.asgi_app()

    def test_returns_a_starlette_app(self, service):
        service.start()
        assert isinstance(service.asgi_app(), Starlette)

    def test_serves_the_mcp_route(self, service):
        service.start()
        _paths = [getattr(r, "path", None) for r in service.asgi_app().routes]
        assert "/mcp" in _paths

    def test_not_available_after_stop(self, service):
        service.start()
        service.stop()
        with pytest.raises(RuntimeError, match="not running"):
            service.asgi_app()

    def test_refuses_to_serve_without_auth(self, log, fake):
        _service = McpHostService(_setting(), clients={"centre": fake})
        _service.start()
        with pytest.raises(RuntimeError, match="no auth"):
            _service.asgi_app()
        _service.stop()


class TestHealth:
    def test_reports_the_node(self, service):
        service.start()
        _res = service.health()
        assert _res["kind"] == "mcphost"
        assert _res["is_running"] is True
        assert _res["nodes"] == [{"name": "centre", "reachable": True, "state": "running"}]

    def test_unreachable_node_does_not_break_health(self, service, fake):
        service.start()
        fake.raises = NodeUnavailableError("gone")
        _res = service.health()
        assert _res["is_running"] is True
        assert _res["nodes"] == [{"name": "centre", "reachable": False}]

    def test_reports_every_node(self, log):
        _up, _down = FakeNodeClient(), FakeNodeClient()
        _service = McpHostService(_setting(a=1, b=1), clients={"a": _up, "b": _down})
        _service.start()
        _down.raises = NodeUnavailableError("gone")
        assert [(n["name"], n["reachable"]) for n in _service.health()["nodes"]] == [("a", True), ("b", False)]
        _service.stop()

    def test_before_start(self, log):
        _res = McpHostService(_setting()).health()
        assert _res["is_running"] is False
        assert _res["nodes"] == [{"name": "centre", "reachable": False}]


class TestRealHttpClient:
    def test_wrong_endpoint_fails_the_start(self, log, monkeypatch):
        def _refuse(request):
            raise httpx.ConnectError("refused")

        _http = httpx.Client(transport=httpx.MockTransport(_refuse), base_url="http://centre:8800")
        _client = HttpNodeClient(endpoint="http://centre:8800", token="t0ken", client=_http)
        monkeypatch.setattr(HttpNodeClient, "from_setting", classmethod(lambda cls, setting: _client))
        _service = McpHostService(_setting())
        with pytest.raises(NodeUnavailableError):
            _service.start()
        assert _service.state == ServiceState.FAILED
