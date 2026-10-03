from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.aliyun.aliyun import AliyunIdentity
from app.resource.store.oss.store import OSSStore
from app.resource.store.oss.table import OSSStoreTable


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


def _fake_client() -> MagicMock:
    _client = MagicMock()
    _client.list_folders.return_value = []
    _storage: dict[str, bytes] = {}

    def _write_bytes(key, data):
        _storage[key] = data

    def _read_bytes(key):
        if key not in _storage:
            raise FileNotFoundError(key)
        return _storage[key]

    _client.write_bytes.side_effect = _write_bytes
    _client.read_bytes.side_effect = _read_bytes
    return _client


def _make_table(monkeypatch, name: str = "tbl") -> OSSStoreTable:
    _client = _fake_client()
    monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
    store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")
    db = store.database("db")
    return db.table(name)


class TestOSSStoreTableGovernedConstruction:
    def test_direct_construction_without_authorized_raises_validation_error(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        with pytest.raises(ValidationError):
            OSSStoreTable(
                name="tbl2",
                bucket=tbl.bucket,
                region=tbl.region,
                key="store/db/tbl2.json",
                identity=tbl.identity,
            )


class TestOSSStoreTableDeriveKey:
    def test_key_ending_with_slash_raises_value_error(self):
        with pytest.raises(ValidationError):
            OSSStoreTable(
                name="tbl",
                bucket="my-bucket",
                region="cn-hangzhou",
                key="store/db/tbl/",
                identity=AliyunIdentity.default(),
                _authorized=True,
            )

    def test_empty_key_raises_value_error(self):
        with pytest.raises(ValidationError):
            OSSStoreTable(
                name="tbl",
                bucket="my-bucket",
                region="cn-hangzhou",
                key="",
                identity=AliyunIdentity.default(),
                _authorized=True,
            )


class TestOSSStoreTableWriteRead:
    def test_write_then_read_returns_same_value(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.write("k1", {"a": 1})
        assert tbl.read("k1") == {"a": 1}

    def test_write_upserts_existing_key(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.write("k1", "v1")
        tbl.write("k1", "v2")
        assert tbl.read("k1") == "v2"

    def test_write_preserves_other_keys(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.write("k1", "v1")
        tbl.write("k2", "v2")
        assert tbl.read("k1") == "v1"
        assert tbl.read("k2") == "v2"

    def test_read_missing_key_returns_none(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.write("k1", "v1")
        assert tbl.read("missing") is None

    def test_read_missing_object_returns_none(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        assert tbl.read("k1") is None


class TestOSSStoreTableWriteErrorHandling:
    def test_write_failure_non_strict_does_not_raise(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.client.write_bytes.side_effect = OSError("network error")
        tbl.write("k1", "v1")  # should not raise

    def test_write_failure_strict_raises(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.client.write_bytes.side_effect = OSError("network error")
        with pytest.raises(OSError):
            tbl.write("k1", "v1", strict=True)


class TestOSSStoreTableDelete:
    def test_deletes_existing_key(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.write("k1", "v1")
        tbl.write("k2", "v2")
        tbl.delete("k1")
        assert tbl.read("k1") is None
        assert tbl.read("k2") == "v2"

    def test_missing_key_non_strict_does_nothing(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.write("k1", "v1")
        tbl.delete("missing")  # should not raise
        assert tbl.read("k1") == "v1"

    def test_missing_key_strict_raises_key_error(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.write("k1", "v1")
        with pytest.raises(KeyError):
            tbl.delete("missing", strict=True)

    def test_missing_object_non_strict_does_nothing(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.delete("missing")  # should not raise, object never existed

    def test_missing_object_strict_raises_key_error(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        with pytest.raises(KeyError):
            tbl.delete("missing", strict=True)


class TestOSSStoreTableLoadContentErrorHandling:
    def test_corrupted_json_non_strict_read_returns_none(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.client.read_bytes.side_effect = None
        tbl.client.read_bytes.return_value = b"not valid json"
        assert tbl.read("k1") is None

    def test_corrupted_json_strict_read_raises(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        tbl.client.read_bytes.side_effect = None
        tbl.client.read_bytes.return_value = b"not valid json"
        with pytest.raises(json.JSONDecodeError):
            tbl.read("k1", strict=True)


class TestOSSStoreTableExport:
    def test_export_includes_identity_name(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        assert tbl.export()["identity"] == tbl.identity.name

    def test_export_includes_name_and_tags(self, monkeypatch):
        tbl = _make_table(monkeypatch)
        _result = tbl.export()
        assert _result["name"] == tbl.name
        assert _result["tags"]["name"] == tbl.name
