from __future__ import annotations

from pathlib import Path

import pytest
import requests

from app.internal.logstream import LogStream
from app.resource._global.identities import GlobalIdentities
from app.resource.accessory.retry.retry import Retry
from app.resource.source.nswvg.index import NSWVGIndex
from app.resource.source.nswvg.remote import (
    CRITICAL_ERROR_EXPRS,
    NSWVGIndexPage,
    NSWVGPSIFileKind,
)
from app.resource.store._common._table import BaseTable
from app.resource.store.file.store import FileStore

_SAMPLE: str = (Path(__file__).parent / "index.sample.html").read_text(encoding="utf-8")
_RETRY_SLEEP = "app.resource.accessory.retry.retry.time.sleep"
_JITTER_SLEEP = "app.resource.accessory.jitter.jitter.time.sleep"


@pytest.fixture(autouse=True)
def _reset_global_identities():
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(_RETRY_SLEEP, lambda _s: None)
    monkeypatch.setattr(_JITTER_SLEEP, lambda _s: None)


@pytest.fixture
def table(tmp_path) -> BaseTable:
    _store = FileStore(name="s", path=str(tmp_path / "store"))
    return _store.table(
        database=NSWVGIndex.database,
        name=NSWVGIndex.table_name,
        ttl_hours=NSWVGIndex.ttl_hours,
    )


@pytest.fixture
def index(table) -> NSWVGIndex:
    return NSWVGIndex(
        table=table,
        timeout_seconds=1.0,
        log_stream=LogStream(name="nswvg_index_test"),
    )


def _http_error(status: int, reason: str, url: str) -> requests.HTTPError:
    _kind = "Client" if status < 500 else "Server"
    return requests.HTTPError(f"{status} {_kind} Error: {reason} for url: {url}")


class TestCriticalErrorExprs:
    def _retry(self) -> Retry:
        return Retry(max_retries=3, interval=0, critical_error_exprs=CRITICAL_ERROR_EXPRS)

    def test_404_is_critical(self):
        _err = _http_error(404, "Not Found", "https://h/__psi/weekly/20260105.zip")
        with pytest.raises(requests.HTTPError):
            self._retry().run(error=_err)

    def test_challenge_is_critical(self):
        with pytest.raises(requests.HTTPError):
            self._retry().run(error=requests.HTTPError("Request blocked by challenge"))

    def test_503_is_retried(self):
        _err = _http_error(503, "Service Unavailable", "https://h/__psi/weekly/20260105.zip")
        assert self._retry().run(error=_err).value == "RETRY"

    def test_date_in_url_is_not_mistaken_for_status(self):
        # 20260504 contains "504"
        _err = _http_error(503, "Service Unavailable", "https://h/__psi/weekly/20260504.zip")
        assert self._retry().run(error=_err).value == "RETRY"


class TestIndexListFiles:
    def test_fetch_parses_and_caches(self, index, table, monkeypatch):
        _calls: list[int] = []

        def _fetch(self, timeout_seconds=None):
            _calls.append(1)
            return _SAMPLE

        monkeypatch.setattr(NSWVGIndexPage, "fetch", _fetch)

        _first = index.list_files()
        _second = index.list_files()

        assert len(_calls) == 1
        assert {f.kind for f in _first} == {NSWVGPSIFileKind.WEEK, NSWVGPSIFileKind.YEAR}
        assert [f.key for f in _second] == [f.key for f in _first]
        assert table.read(key="remote_files", strict=False) is not None

    def test_force_bypasses_cache(self, index, monkeypatch):
        _calls: list[int] = []

        def _fetch(self, timeout_seconds=None):
            _calls.append(1)
            return _SAMPLE

        monkeypatch.setattr(NSWVGIndexPage, "fetch", _fetch)

        index.list_files()
        index.list_files(force=True)

        assert len(_calls) == 2

    def test_transient_error_is_retried(self, index, monkeypatch):
        _calls: list[int] = []

        def _fetch(self, timeout_seconds=None):
            _calls.append(1)
            if len(_calls) == 1:
                raise _http_error(503, "Service Unavailable", "https://h/")
            return _SAMPLE

        monkeypatch.setattr(NSWVGIndexPage, "fetch", _fetch)

        assert index.list_files()
        assert len(_calls) == 2

    def test_critical_error_is_not_retried(self, index, monkeypatch):
        _calls: list[int] = []

        def _fetch(self, timeout_seconds=None):
            _calls.append(1)
            raise _http_error(404, "Not Found", "https://h/")

        monkeypatch.setattr(NSWVGIndexPage, "fetch", _fetch)

        with pytest.raises(requests.HTTPError):
            index.list_files()
        assert len(_calls) == 1

    def test_class_level_retry_is_not_mutated(self, index, monkeypatch):
        def _fetch(self, timeout_seconds=None):
            raise _http_error(503, "Service Unavailable", "https://h/")

        monkeypatch.setattr(NSWVGIndexPage, "fetch", _fetch)

        with pytest.raises(requests.HTTPError):
            index.list_files()
        assert NSWVGIndex.retry._attempt == 0
