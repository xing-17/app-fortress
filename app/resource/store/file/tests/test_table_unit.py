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


class TestFileStoreTableWriteRead:
    def test_write_then_read_returns_same_value(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", {"a": 1})
        assert tbl.read("k1") == {"a": 1}

    def test_write_creates_parent_directories_and_file(self, tmp_path):
        tbl = _make_table(tmp_path)
        tbl.write("k1", "v1")
        assert tbl.path.exists()
        assert json.loads(tbl.path.read_bytes()) == {"k1": "v1"}

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
