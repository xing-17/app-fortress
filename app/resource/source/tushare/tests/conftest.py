from __future__ import annotations

import time

import pandas as pd
import pytest

from app.internal.logstream import LogStream
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.vault import LocalVault
from app.resource.source.tushare import session as session_module
from app.resource.source.tushare.session import TushareSession
from app.resource.store.file.store import FileStore


class FakeApi:
    """Stands in for `tushare.pro_api()`; `demo` honours limit/offset like a paginated endpoint."""

    def __init__(self) -> None:
        self.rows: list[tuple] = []
        self.calls: list[dict] = []
        self.fail_times: int = 0
        self.tradecal: pd.DataFrame = pd.DataFrame()

    def demo(self, **params) -> pd.DataFrame:
        self.calls.append(params)
        if self.fail_times > 0:
            self.fail_times -= 1
            raise Exception("boom")
        _offset: int = params.get("offset", 0)
        _limit: int = params.get("limit", len(self.rows))
        return pd.DataFrame(self.rows[_offset : _offset + _limit], columns=["id", "part"])

    def trade_cal(self, **params) -> pd.DataFrame:
        self.calls.append(params)
        return self.tradecal


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    # GlobalIdentities is process-wide state; Retry/Jitter must not really sleep.
    GlobalIdentities.reset()
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    yield
    GlobalIdentities.reset()


@pytest.fixture
def api(monkeypatch):
    _api = FakeApi()
    monkeypatch.setattr(session_module.tushare, "pro_api", lambda *_a, **_k: _api)
    return _api


@pytest.fixture
def session(api):
    return TushareSession(key="k", ttl_hours=1)


@pytest.fixture
def vault(tmp_path):
    return LocalVault(name="v", path=tmp_path / "vault")


@pytest.fixture
def store(tmp_path):
    return FileStore(name="s", path=str(tmp_path / "store"))


@pytest.fixture
def log_stream():
    return LogStream(name="test_tushare", console_verbose=False)
