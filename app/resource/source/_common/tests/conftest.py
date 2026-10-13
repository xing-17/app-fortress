from __future__ import annotations

import logging

import pytest

from app.internal.logstream import LogStream
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.vault import LocalVault
from app.resource.source._common.tests.fakes.base import FakeSource
from app.resource.store.file.store import FileStore


class RecordCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
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
    _stream = LogStream(name="test_source", console_verbose=False)
    _stream.collector = RecordCollector()
    _stream.addHandler(_stream.collector)
    return _stream


@pytest.fixture
def source(vault, store, log_stream):
    return FakeSource(name="src", vault=vault, store=store, log_stream=log_stream)
