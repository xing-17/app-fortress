from __future__ import annotations

import time

import pytest

from app.internal.logstream import LogStream
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.vault import LocalVault
from app.resource.source.rba import RBASource
from app.resource.store.file.store import FileStore


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    # GlobalIdentities is process-wide state; Retry must not really sleep.
    GlobalIdentities.reset()
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    yield
    GlobalIdentities.reset()


@pytest.fixture
def vault(tmp_path):
    return LocalVault(name="v", path=tmp_path / "vault")


@pytest.fixture
def store(tmp_path):
    return FileStore(name="s", path=str(tmp_path / "store"))


@pytest.fixture
def log_stream():
    return LogStream(name="test_rba", console_verbose=False)


@pytest.fixture
def source(vault, store, log_stream):
    return RBASource(name="rba", vault=vault, store=store, log_stream=log_stream)
