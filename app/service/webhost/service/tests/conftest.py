from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from app.internal.logstream import LogStream
from app.resource._global.logstreams import GlobalLogStreams
from app.service._common.access import AccessAuth
from app.service._common.auth import TokenAuth
from app.service._common.tests._assertions import StaticKeys, make_key
from app.service.mcphost.service.tests.fakes import FakeNodeClient
from app.service.node.service.errors import NodeUnavailableError
from app.service.webhost.service.service import WebHostService
from app.setting.service import AccessSetting, AuthSetting, WebHostServiceSetting

BASE = "http://127.0.0.1:8802"
HTML = {"Accept": "text/html"}
JSON = {"Accept": "application/json"}


@pytest.fixture
def log(monkeypatch):
    _log = MagicMock(spec=LogStream)
    monkeypatch.setattr(GlobalLogStreams, "resolve", lambda value, default: _log)
    return _log


@pytest.fixture
def fake():
    _fake = FakeNodeClient()
    _fake.node_health = {"state": "running", "is_running": True, "sessions": 1, "busy_sessions": 0}
    _fake.snapshots = [
        {
            "timestamp": 1_700_000_000.0 + i * 60,
            "cpu_percent": 10.0 + i,
            "mem_percent": 40.0,
            "mem_used_mb": 4096,
            "mem_total_mb": 16384,
            "disk_percent": 50.0,
            "disk_used_mb": 100_000,
            "disk_total_mb": 200_000,
        }
        for i in range(5)
    ]
    _fake.sources = [{"name": "src", "provider": "fake", "datasets": ["alpha"]}]
    _fake.runs = [{"id": "run_0", "status": "completed", "height": 3, "width": 2, "started_at": 1.0, "duration": 2.0}]
    return _fake


@pytest.fixture
def auth(tmp_path):
    _key = tmp_path / "web.key"
    _key.write_text("w" * 64 + "\n", encoding="utf-8")
    _key.chmod(0o600)
    return TokenAuth(AuthSetting(masterfile=str(_key), tokens=[{"name": "me"}, {"name": "gone", "revoked": True}]))


def make_setting(**extra) -> WebHostServiceSetting:
    _nodes = [
        {"name": "centre", "endpoint": "http://centre:8800", "token": "t0ken"},
        {"name": "ghost", "endpoint": "http://ghost:8800", "token": "t0ken"},
    ]
    return WebHostServiceSetting(nodes=_nodes, **extra)


class _DownClient(FakeNodeClient):
    def health(self):
        raise NodeUnavailableError("node http://ghost:8800 is unreachable: ConnectError")


@pytest.fixture
def service(log, fake, auth):
    _service = WebHostService(make_setting(), clients={"centre": fake, "ghost": _DownClient()}, auth=auth)
    _service.start()
    yield _service
    _service.stop()


@pytest.fixture
def web(service):
    with TestClient(
        service.asgi_app(), base_url=BASE, follow_redirects=False, raise_server_exceptions=False
    ) as _client:
        yield _client


@pytest.fixture
def signed_in(web, auth):
    _res = web.post("/login", data={"token": auth.token("me"), "next": "/"})
    assert _res.status_code == 303
    return web


@pytest.fixture
def access_setting():
    return AccessSetting(
        team_domain="team-x.cloudflareaccess.com",
        audience="a" * 64,
        users=[{"email": "me@example.com", "name": "me"}],
    )


@pytest.fixture
def signing_key():
    return make_key()


@pytest.fixture
def behind_access(log, fake, auth, access_setting, signing_key):
    _access = AccessAuth(access_setting, keys=StaticKeys(signing_key))
    _service = WebHostService(
        make_setting(access=access_setting),
        clients={"centre": fake, "ghost": _DownClient()},
        auth=auth,
        access=_access,
    )
    _service.start()
    with TestClient(_service.asgi_app(), base_url=BASE, follow_redirects=False) as _client:
        yield _client
    _service.stop()
