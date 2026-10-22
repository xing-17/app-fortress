from __future__ import annotations

import pytest

from app.service.node.client.localnode import LocalNodeClient
from app.service.node.service.auth import Principal


class TestLocalNodeClient:
    def test_queries_run_as_the_local_principal_by_default(self, service, monkeypatch):
        _seen = []
        monkeypatch.setattr(service, "query", lambda caller, sql: _seen.append(caller))
        LocalNodeClient(service).query("SELECT 1")
        assert _seen == [Principal(name="local")]

    def test_queries_run_as_the_given_principal(self, service, monkeypatch):
        _seen = []
        monkeypatch.setattr(service, "query", lambda caller, sql: _seen.append(caller))
        LocalNodeClient(service, caller=Principal(name="bob")).query("SELECT 1")
        assert _seen == [Principal(name="bob")]

    def test_close_does_not_stop_the_service(self, service):
        LocalNodeClient(service).close()
        assert service.is_running

    def test_requires_a_running_service(self, service):
        service.stop()
        with pytest.raises(RuntimeError, match="not running"):
            LocalNodeClient(service).list_sources()
