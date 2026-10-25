from __future__ import annotations

import time

import pytest
import requests

from app.internal.logstream import LogStream
from app.resource._client.web.client import WebClient
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.vault import LocalVault
from app.resource.store.file.store import FileStore

# Real rows of `JV/all?startPeriod=2024&endPeriod=2025&format=csv`
JV_CSV: str = (
    "DATAFLOW,MEASURE,SECTOR,INDUSTRY,TSEST,REGION,FREQ,TIME_PERIOD,OBS_VALUE,UNIT_MEASURE,UNIT_MULT,OBS_STATUS,OBS_COMMENT,DECIMALS\n"
    "ABS:JV(1.0),M2,7,O,10,AUS,Q,2024-Q1,1,NUM,3,,,1\n"
    "ABS:JV(1.0),M2,7,O,10,AUS,Q,2024-Q2,0.9,NUM,3,,,1\n"
    "ABS:JV(1.0),M1,7,Q,10,AUS,Q,2024-Q1,n/a,NUM,3,,,0\n"
)


def make_response(
    status: int,
    body: str,
    url: str = "https://data.api.abs.gov.au/rest/data/JV/all",
) -> requests.Response:
    _resp = requests.Response()
    _resp.status_code = status
    _resp.reason = {200: "OK", 404: "Not Found", 422: "Unprocessable Entity", 503: "Service Unavailable"}.get(
        status, ""
    )
    _resp.url = url
    _resp._content = body.encode("utf-8")
    return _resp


class FakeClient(WebClient):
    """Stands in for `WebClient`; replies are consumed in order, the last one repeats."""

    def __init__(self) -> None:
        super().__init__()
        self.replies: list[requests.Response] = []
        self.calls: list[dict] = []

    def request(self, method, url, params=None, headers=None, stream=False, timeout=None):
        self.calls.append({"method": method, "url": url, "params": params, "timeout": timeout})
        _idx: int = min(len(self.calls), len(self.replies)) - 1
        _resp: requests.Response = self.replies[_idx]
        _resp.raise_for_status()
        return _resp


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    # GlobalIdentities is process-wide state; Retry/Jitter must not really sleep.
    GlobalIdentities.reset()
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    yield
    GlobalIdentities.reset()


@pytest.fixture
def client():
    return FakeClient()


@pytest.fixture
def vault(tmp_path):
    return LocalVault(name="v", path=tmp_path / "vault")


@pytest.fixture
def store(tmp_path):
    return FileStore(name="s", path=str(tmp_path / "store"))


@pytest.fixture
def log_stream():
    return LogStream(name="test_abs", console_verbose=False)
