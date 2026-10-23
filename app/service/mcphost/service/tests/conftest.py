from __future__ import annotations

import io
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from app.internal.logstream import LogStream
from app.resource._global.identities import GlobalIdentities
from app.resource._global.logstreams import GlobalLogStreams
from app.resource._global.sources import GlobalSources
from app.resource.asset.local.vault import LocalVault
from app.resource.source._common.tests.fakes.base import FakeSource
from app.resource.store.file.store import FileStore
from app.service._common.auth import TokenAuth
from app.service.node.client.httpnode import HttpNodeClient
from app.service.node.client.localnode import LocalNodeClient
from app.service.node.service.http import create_app
from app.service.node.service.service import NodeService
from app.setting.service import AuthSetting, NodeServiceSetting


@pytest.fixture(autouse=True)
def _reset_globals():
    GlobalIdentities.reset()
    GlobalSources.reset()
    yield
    GlobalSources.reset()
    GlobalIdentities.reset()


@pytest.fixture
def log(monkeypatch):
    _log = MagicMock(spec=LogStream)
    monkeypatch.setattr(GlobalLogStreams, "resolve", lambda value, default: _log)
    return _log


@pytest.fixture
def source(tmp_path):
    _source = FakeSource(
        name="src",
        vault=LocalVault(name="v", path=tmp_path / "vault"),
        store=FileStore(name="s", path=str(tmp_path / "store")),
        log_stream=LogStream(name="src", console_verbose=False),
    )
    GlobalSources.sources = {"src": _source}
    return _source


@pytest.fixture
def node_service(log, source):
    _service = NodeService(NodeServiceSetting())
    _service.start()
    yield _service
    _service.stop()


@pytest.fixture
def node_auth(tmp_path):
    _key = tmp_path / "password.key"
    _key.write_text("k" * 64 + "\n", encoding="utf-8")
    _key.chmod(0o600)
    return TokenAuth(AuthSetting(masterfile=str(_key), tokens=[{"name": "mcphost"}]))


@pytest.fixture
def user_auth(tmp_path):
    _key = tmp_path / "users.key"
    _key.write_text("u" * 64 + "\n", encoding="utf-8")
    _key.chmod(0o600)
    _tokens = [{"name": "phone"}, {"name": "gone", "revoked": True}]
    return TokenAuth(AuthSetting(masterfile=str(_key), tokens=_tokens))


@pytest.fixture(params=["local", "http"])
def node_client(request, node_service, node_auth):
    if request.param == "local":
        _client = LocalNodeClient(node_service)
    else:
        _app = TestClient(create_app(node_service, node_auth), raise_server_exceptions=False)
        _client = HttpNodeClient(
            endpoint="http://testserver",
            token=node_auth.token("mcphost"),
            client=_app,
        )
    yield _client
    _client.close()


def write_assetfile(source, dataset_name, name, df, partitions=None):
    _dataset = source.dataset(dataset_name)
    _file = _dataset.asset.assetfile(name, partitions=partitions)
    _buffer = io.BytesIO()
    df.write_parquet(_buffer)
    _dataset.write_assetfile(_file, _buffer.getvalue())
    _dataset.write_metadata(_file, _dataset.get_metadata(df))
    return _file
