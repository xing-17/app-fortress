from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import pytest

from app.internal.logstream import LogStream
from app.resource._global.identities import GlobalIdentities
from app.resource.asset.local.vault import LocalVault
from app.resource.store.file.store import FileStore


class RecordCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def modern_b(
    district: str = "001",
    property_id: str = "100",
    counter: str = "1",
    download_time: str = "20260105 09:30",
    contract_date: str = "20260102",
    settlement_date: str = "20260103",
    price: str = "500000",
    area: str = "600.5",
) -> str:
    # 25 fields after split: `B`, 23 values, trailing empty
    _f: list[str] = [
        "B", district, property_id, counter, download_time, "", "U1", "12", "MAIN ST", "SYDNEY", "2000",
        area, "M", contract_date, settlement_date, price, "R2", "RES", "HOUSE", "7",
        "A", "S", "100", "AB123", "",
    ]  # fmt: skip
    return ";".join(_f)


def modern_c(
    district: str = "001",
    property_id: str = "100",
    counter: str = "1",
    land: str = "LOT 1 DP 123",
) -> str:
    return ";".join(["C", district, property_id, counter, "", land, ""])


def archive_b(
    contract_date: str = "02/01/1995",
    price: str = "250000",
) -> str:
    # 22 fields after split: `B`, 20 values, trailing empty
    _f: list[str] = [
        "B", "001", "RP", "V1", "100", "U1", "12", "MAIN ST", "SYDNEY", "2000",
        contract_date, price, "LOT 1 DP 9", "600", "M", "20x30", "R", "R2", "", "", "", "",
    ]  # fmt: skip
    return ";".join(_f)


def dat(*lines: str) -> bytes:
    return "\r\n".join(["A;header", *lines, "Z;footer"]).encode("utf-8")


def zip_bytes(files: dict[str, bytes]) -> bytes:
    _buf = io.BytesIO()
    with zipfile.ZipFile(_buf, "w") as _zf:
        for _name, _data in files.items():
            _zf.writestr(_name, _data)
    return _buf.getvalue()


def make_item(
    root: Path,
    key: str,
    files: dict[str, bytes] | None = None,
) -> Path:
    _dir: Path = root / key
    _dir.mkdir(parents=True, exist_ok=True)
    for _name, _data in (files or {}).items():
        (_dir / _name).write_bytes(_data)
    return _dir


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
    _stream = LogStream(name="test_nswvg", console_verbose=False)
    _stream.collector = RecordCollector()
    _stream.addHandler(_stream.collector)
    return _stream


@pytest.fixture
def provision_root(tmp_path):
    return tmp_path / "provision"
