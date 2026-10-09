from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.resource._client.oss.client import OSSClient
from app.resource._global.identities import GlobalIdentities
from app.resource.store.oss.database import OSSStoreDatabase
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
    _client.list_objects.return_value = []
    return _client


def _make_store(monkeypatch, client: MagicMock | None = None) -> OSSStore:
    _client = client or _fake_client()
    monkeypatch.setattr(OSSClient, "get_client", lambda **kwargs: _client)
    return OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou")


class TestOSSStoreDatabaseGovernedConstruction:
    def test_direct_construction_without_authorized_raises_validation_error(self, monkeypatch):
        store = _make_store(monkeypatch)
        with pytest.raises(ValidationError):
            OSSStoreDatabase(
                name="db",
                bucket=store.bucket,
                region=store.region,
                prefix="store/db",
                identity=store.identity,
            )


class TestOSSStoreDatabaseDerivePrefix:
    def test_prefix_built_from_store_prefix_and_name(self, monkeypatch):
        store = _make_store(monkeypatch)
        db = store.database("newdb")
        assert db.prefix == "store/newdb"


class TestOSSStoreDatabaseDeriveIdentity:
    def test_inherits_store_identity(self, monkeypatch):
        store = _make_store(monkeypatch)
        db = store.database("newdb")
        assert db.identity is store.identity


class TestOSSStoreDatabaseClient:
    def test_client_property_resolves_via_oss_client_get_client(self, monkeypatch):
        _captured = {}
        _client = _fake_client()

        def _fake_get_client(**kwargs):
            _captured.update(kwargs)
            return _client

        monkeypatch.setattr(OSSClient, "get_client", _fake_get_client)
        store = OSSStore(name="s", bucket="my-bucket", region="cn-hangzhou", in_vpc=True)
        db = store.database("db")
        assert db.client is _client
        assert _captured == {
            "bucket": "my-bucket",
            "region": "cn-hangzhou",
            "identity": store.identity,
            "in_vpc": True,
        }


class TestOSSStoreDatabaseListTables:
    def test_builds_table_for_each_json_object(self, monkeypatch):
        _client = _fake_client()
        _client.list_objects.return_value = [
            {"bucket": "my-bucket", "key": "store/db/tbl_a.json"},
        ]
        store = _make_store(monkeypatch, client=_client)
        db = store.database("db")
        assert [t.name for t in db.list_tables()] == ["tbl_a"]

    def test_forwards_prefix_and_pattern_to_client(self, monkeypatch):
        _captured = {}

        def _fake_list_objects(**kwargs):
            _captured.update(kwargs)
            return []

        _client = _fake_client()
        _client.list_objects.side_effect = _fake_list_objects
        store = _make_store(monkeypatch, client=_client)
        db = store.database("db")
        db.list_tables()
        assert _captured == {
            "prefix": "store/db/",
            "pattern": "*.json",
            "recursive": False,
        }

    def test_table_inherits_database_identity(self, monkeypatch):
        _client = _fake_client()
        _client.list_objects.return_value = [{"bucket": "my-bucket", "key": "store/db/tbl.json"}]
        store = _make_store(monkeypatch, client=_client)
        db = store.database("db")
        assert db.list_tables()[0].identity is db.identity

    def test_no_objects_returns_empty_list(self, monkeypatch):
        store = _make_store(monkeypatch)
        db = store.database("db")
        assert db.list_tables() == []


class TestOSSStoreDatabaseTableMethod:
    def test_builds_table_with_json_extension_under_database_prefix(self, monkeypatch):
        store = _make_store(monkeypatch)
        db = store.database("db")
        tbl = db.table("mytable")
        assert isinstance(tbl, OSSStoreTable)
        assert tbl.key == "store/db/mytable.json"

    def test_table_inherits_database_identity(self, monkeypatch):
        store = _make_store(monkeypatch)
        db = store.database("db")
        tbl = db.table("mytable")
        assert tbl.identity is db.identity

    @pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b", "a\\b"])
    def test_rejects_invalid_names(self, monkeypatch, bad_name):
        store = _make_store(monkeypatch)
        db = store.database("db")
        with pytest.raises(ValidationError):
            db.table(bad_name)


class TestOSSStoreDatabaseDelete:
    def test_deletes_existing_table_object(self, monkeypatch):
        _client = _fake_client()
        _client.get_object.return_value = {"key": "store/db/mytable.json"}
        store = _make_store(monkeypatch, client=_client)
        db = store.database("db")
        db.delete("mytable")
        _client.delete_object.assert_called_once_with("store/db/mytable.json")

    def test_missing_table_non_strict_does_nothing(self, monkeypatch):
        _client = _fake_client()
        _client.get_object.side_effect = FileNotFoundError("missing")
        store = _make_store(monkeypatch, client=_client)
        db = store.database("db")
        db.delete("missing")  # should not raise
        _client.delete_object.assert_not_called()

    def test_missing_table_strict_raises_file_not_found_error(self, monkeypatch):
        _client = _fake_client()
        _client.get_object.side_effect = FileNotFoundError("missing")
        store = _make_store(monkeypatch, client=_client)
        db = store.database("db")
        with pytest.raises(FileNotFoundError):
            db.delete("missing", strict=True)
