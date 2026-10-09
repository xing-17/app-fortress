from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.resource._global.identities import GlobalIdentities
from app.resource.store.file.database import FileStoreDatabase
from app.resource.store.file.store import FileStore
from app.resource.store.file.table import FileStoreTable


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


def _make_store(tmp_path) -> FileStore:
    return FileStore(name="s", path=str(tmp_path))


class TestFileStoreDatabaseGovernedConstruction:
    def test_direct_construction_without_authorized_raises_validation_error(self, tmp_path):
        store = _make_store(tmp_path)
        with pytest.raises(ValidationError):
            FileStoreDatabase(name="db", path=tmp_path / "db", identity=store.identity)


class TestFileStoreDatabaseDerivePath:
    def test_path_is_created_when_missing(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("newdb")
        assert db.path.is_dir()

    def test_path_pointing_to_existing_file_raises_value_error(self, tmp_path):
        store = _make_store(tmp_path)
        (tmp_path / "a_file").write_text("content")
        with pytest.raises(ValueError):
            store.database("a_file")


class TestFileStoreDatabaseDeriveIdentity:
    def test_inherits_store_identity(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("newdb")
        assert db.identity is store.identity


class TestFileStoreDatabaseFrn:
    def test_frn_includes_path(self, tmp_path):
        db = _make_store(tmp_path).database("db")
        assert db.frn == f"store:database:platform=local:storesystem=file:path={db.path}"

    def test_same_name_under_different_stores_has_different_frn(self, tmp_path):
        first = FileStore(name="a", path=str(tmp_path / "a")).database("db")
        second = FileStore(name="b", path=str(tmp_path / "b")).database("db")
        assert first.frn != second.frn


class TestFileStoreDatabaseListTables:
    def test_only_json_files_are_listed_as_tables(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("db")
        (db.path / "tbl_a.json").write_text("{}")
        (db.path / "not_a_table.txt").write_text("x")
        assert [t.name for t in db.list_tables()] == ["tbl_a"]

    def test_table_name_is_file_stem(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("db")
        (db.path / "my_table.json").write_text("{}")
        assert db.list_tables()[0].name == "my_table"

    def test_table_inherits_database_identity(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("db")
        (db.path / "tbl.json").write_text("{}")
        assert db.list_tables()[0].identity is db.identity

    def test_no_json_files_returns_empty_list(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("db")
        assert db.list_tables() == []


class TestFileStoreDatabaseTableMethod:
    def test_builds_table_with_json_extension_under_database_path(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("db")
        tbl = db.table("mytable")
        assert isinstance(tbl, FileStoreTable)
        assert tbl.path == db.path / "mytable.json"

    def test_table_does_not_create_file_on_disk(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("db")
        tbl = db.table("mytable")
        assert not tbl.path.exists()

    def test_table_inherits_database_identity(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("db")
        tbl = db.table("mytable")
        assert tbl.identity is db.identity

    @pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b", "a\\b"])
    def test_rejects_invalid_names(self, tmp_path, bad_name):
        store = _make_store(tmp_path)
        db = store.database("db")
        with pytest.raises(ValidationError):
            db.table(bad_name)


class TestFileStoreDatabaseDelete:
    def test_deletes_existing_table_file(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("db")
        db.table("mytable").write("k", "v")
        assert (db.path / "mytable.json").exists()
        db.delete("mytable")
        assert not (db.path / "mytable.json").exists()

    def test_missing_table_non_strict_does_nothing(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("db")
        db.delete("missing")  # should not raise

    def test_missing_table_strict_raises_file_not_found_error(self, tmp_path):
        store = _make_store(tmp_path)
        db = store.database("db")
        with pytest.raises(FileNotFoundError):
            db.delete("missing", strict=True)
