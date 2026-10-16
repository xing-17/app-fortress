from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.resource._client.local.client import LocalObjectClient
from app.resource._global.identities import GlobalIdentities
from app.resource.store.file.store import FileStore
from app.resource.store.file.table import FileStoreTable


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


def _make_table(tmp_path, name: str = "tbl") -> FileStoreTable:
    store = FileStore(name="s", path=str(tmp_path))
    db = store.database("db")
    return db.table(name)


class TestFileStoreTableGovernedConstruction:
    def test_direct_construction_without_authorized_raises_validation_error(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        with pytest.raises(ValidationError):
            FileStoreTable(name="tbl", path=tmp_path / "tbl.json", identity=store.identity)


class TestFileStoreTableDerivePath:
    def test_non_existent_path_is_accepted(self, tmp_path):
        tbl = _make_table(tmp_path)
        assert not tbl.path.exists()

    def test_path_pointing_to_existing_directory_raises_value_error(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        db = store.database("db")
        (db.path / "tbl.json").mkdir()
        with pytest.raises(ValueError):
            db.table("tbl")


class TestFileStoreTableFrn:
    def test_frn_includes_path(self, tmp_path):
        tbl = _make_table(tmp_path)
        assert tbl.frn == f"store:database:table:platform=local:storesystem=file:path={tbl.path}"

    def test_same_name_under_different_databases_has_different_frn(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        assert store.table("db_a", "tbl").frn != store.table("db_b", "tbl").frn


class TestFileStoreTableWriteRead:
    def test_write_then_read_returns_same_value(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", {"a": 1})
        assert tbl.read("k1") == {"a": 1}

    def test_write_creates_parent_directories_and_file(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        assert tbl.path.exists()
        _envelope = json.loads(tbl.path.read_bytes())["k1"]
        assert _envelope["data"] == "v1"
        assert _envelope["key"] == "k1"
        assert _envelope["ttl"] is None
        assert isinstance(_envelope["written_at"], float)

    def test_write_upserts_existing_key(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        tbl.write("k1", "v2")
        assert tbl.read("k1") == "v2"

    def test_write_preserves_other_keys(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        tbl.write("k2", "v2")
        assert tbl.read("k1") == "v1"
        assert tbl.read("k2") == "v2"

    def test_read_missing_key_returns_none(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        assert tbl.read("missing") is None

    def test_read_missing_file_returns_none(self, tmp_path):
        tbl = _make_table(tmp_path)
        assert tbl.read("k1") is None

    def test_read_with_no_key_returns_unwrapped_dict_of_all_data(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        tbl.write("k2", "v2")
        assert tbl.read() == {"k1": "v1", "k2": "v2"}


class TestFileStoreTableWriteErrorHandling:
    def test_write_failure_non_strict_does_not_raise(self, tmp_path, monkeypatch):
        tbl = _make_table(tmp_path)
        monkeypatch.setattr(LocalObjectClient, "write_bytes", MagicMock(side_effect=OSError("disk full")))
        tbl.write("k1", "v1")  # should not raise

    def test_write_failure_strict_raises(self, tmp_path, monkeypatch):
        tbl = _make_table(tmp_path)
        monkeypatch.setattr(LocalObjectClient, "write_bytes", MagicMock(side_effect=OSError("disk full")))
        with pytest.raises(OSError):
            tbl.write("k1", "v1", strict=True)


class TestFileStoreTableDelete:
    def test_deletes_existing_key(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        tbl.write("k2", "v2")
        tbl.delete("k1")
        assert tbl.read("k1") is None
        assert tbl.read("k2") == "v2"

    def test_missing_key_non_strict_does_nothing(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        tbl.delete("missing")  # should not raise
        assert tbl.read("k1") == "v1"

    def test_missing_key_strict_raises_key_error(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        with pytest.raises(KeyError):
            tbl.delete("missing", strict=True)

    def test_missing_file_non_strict_does_nothing(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.delete("missing")  # should not raise, file never existed

    def test_missing_file_strict_raises_key_error(self, tmp_path):
        tbl = _make_table(tmp_path)
        with pytest.raises(KeyError):
            tbl.delete("missing", strict=True)


class TestFileStoreTableLoadContentErrorHandling:
    def test_corrupted_json_non_strict_read_returns_none(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.path.write_text("not valid json")
        assert tbl.read("k1") is None

    def test_corrupted_json_strict_read_raises(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.path.write_text("not valid json")
        with pytest.raises(json.JSONDecodeError):
            tbl.read("k1", strict=True)


class TestFileStoreTableExport:
    def test_export_includes_identity_name(self, tmp_path):
        tbl = _make_table(tmp_path)
        assert tbl.export()["identity"] == tbl.identity.name

    def test_export_includes_name_and_tags(self, tmp_path):
        tbl = _make_table(tmp_path)
        _result = tbl.export()
        assert _result["name"] == tbl.name
        assert _result["tags"]["name"] == tbl.name


class TestFileStoreTableTTL:
    def test_ttl_hours_defaults_to_none(self, tmp_path):
        tbl = _make_table(tmp_path)
        assert tbl.ttl_hours is None
        assert tbl.ttl_seconds is None

    def test_ttl_hours_is_converted_to_ttl_seconds(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        db = store.database("db")
        tbl = db.table("tbl", ttl_hours=2)
        assert tbl.ttl_hours == 2
        assert tbl.ttl_seconds == 7200.0

    def test_write_records_table_ttl_seconds_in_envelope(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        db = store.database("db")
        tbl = db.table("tbl", ttl_hours=1)
        tbl.write("k1", "v1")
        _envelope = json.loads(tbl.path.read_bytes())["k1"]
        assert _envelope["ttl"] == 3600.0

    def test_write_uses_utc_timestamp(self, tmp_path, monkeypatch):
        from app.internal.util.clock import IClock

        _original = IClock.current_timestamp
        _captured: dict = {}

        def _spy(timezone=None):
            _captured["timezone"] = timezone
            return _original(timezone=timezone)

        monkeypatch.setattr(IClock, "current_timestamp", staticmethod(_spy))
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        assert _captured["timezone"] == "UTC"


class TestFileStoreTableExpire:
    def test_expire_without_ttl_never_removes_keys(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        tbl.expire()
        assert tbl.read("k1") == "v1"

    def test_expire_removes_only_expired_keys(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("alive", "v1")
        tbl.write("dead", "v2")
        # Manually backdate "dead"'s envelope well past a 1-second TTL.
        _content = json.loads(tbl.path.read_bytes())
        _content["dead"]["ttl"] = 1.0
        _content["dead"]["written_at"] -= 1000.0
        tbl.path.write_bytes(json.dumps(_content).encode("utf-8"))

        tbl.expire()

        assert tbl.read("alive") == "v1"
        assert tbl.read("dead") is None

    def test_expire_on_missing_file_does_nothing(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.expire()  # should not raise, should not create the file
        assert not tbl.path.exists()

    def test_expire_on_corrupted_json_raises(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        tbl.path.write_text("not valid json")
        with pytest.raises(json.JSONDecodeError):
            tbl.expire()


class TestFileStoreTableMaxItems:
    @staticmethod
    def _tick(monkeypatch):
        from app.internal.util.clock import IClock

        _counter = iter(range(1, 10_000))
        monkeypatch.setattr(IClock, "current_timestamp", lambda timezone=None: float(next(_counter)))

    def test_max_items_defaults_to_none_and_keeps_all(self, tmp_path, monkeypatch):
        self._tick(monkeypatch)
        tbl = FileStore(name="s", path=str(tmp_path)).database("db").table("tbl", max_items=None)
        for i in range(5):
            tbl.write(f"k{i}", i)
        assert tbl.max_items is None
        assert len(tbl.read()) == 5

    def test_write_drops_oldest_beyond_max_items(self, tmp_path, monkeypatch):
        self._tick(monkeypatch)
        tbl = FileStore(name="s", path=str(tmp_path)).database("db").table("tbl", max_items=2)
        tbl.write("k1", 1)
        tbl.write("k2", 2)
        tbl.write("k3", 3)
        assert tbl.read() == {"k2": 2, "k3": 3}

    def test_updating_existing_key_does_not_evict_and_refreshes_age(self, tmp_path, monkeypatch):
        self._tick(monkeypatch)
        tbl = FileStore(name="s", path=str(tmp_path)).database("db").table("tbl", max_items=2)
        tbl.write("k1", 1)
        tbl.write("k2", 2)
        tbl.write("k1", 10)
        assert tbl.read() == {"k1": 10, "k2": 2}
        tbl.write("k3", 3)
        assert tbl.read() == {"k1": 10, "k3": 3}

    def test_write_batch_keeps_newest_items(self, tmp_path, monkeypatch):
        self._tick(monkeypatch)
        tbl = FileStore(name="s", path=str(tmp_path)).database("db").table("tbl", max_items=2)
        tbl.write("old", 0)
        tbl.write_batch({"a": 1, "b": 2})
        assert tbl.read() == {"a": 1, "b": 2}

    def test_write_batch_larger_than_max_items_keeps_latest_entries(self, tmp_path, monkeypatch):
        self._tick(monkeypatch)
        tbl = FileStore(name="s", path=str(tmp_path)).database("db").table("tbl", max_items=2)
        tbl.write_batch({"a": 1, "b": 2, "c": 3})
        assert tbl.read() == {"b": 2, "c": 3}
