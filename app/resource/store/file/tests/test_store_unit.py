from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.aliyun.identity import AliyunIdentity
from app.resource.identity.local.identity import LocalIdentity
from app.resource.store.file.database import FileStoreDatabase
from app.resource.store.file.store import FileStore
from app.setting._store import FileStoreSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestFileStoreInit:
    def test_storesystem_and_platform_are_fixed(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        assert store.storesystem == StoreSystem.FILE
        assert store.platform == Platform.LOCAL

    def test_default_identity_is_local_identity_default(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        assert store.identity.name == LocalIdentity.default().name

    def test_tags_include_name_storesystem_platform(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        assert store.tags["name"] == "s"
        assert store.tags["storesystem"] == StoreSystem.FILE
        assert store.tags["platform"] == Platform.LOCAL

    def test_default_path_is_relative_store_dir_and_created(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = FileStore(name="s")
        assert store.path == (tmp_path / "store").resolve()
        assert store.path.is_dir()


class TestFileStoreDerivePath:
    def test_string_path_is_resolved_to_path_and_created(self, tmp_path):
        _target = tmp_path / "new_store_dir"
        store = FileStore(name="s", path=str(_target))
        assert isinstance(store.path, Path)
        assert store.path == _target
        assert _target.is_dir()

    def test_existing_directory_path_is_kept(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        assert store.path == tmp_path

    def test_path_pointing_to_existing_file_raises_value_error(self, tmp_path):
        _file = tmp_path / "a_file.txt"
        _file.write_text("content")
        with pytest.raises(ValueError):
            FileStore(name="s", path=str(_file))


class TestFileStoreDeriveIdentity:
    def test_resolves_named_identity(self, tmp_path):
        _identity = LocalIdentity(name="registered_local_identity")
        GlobalIdentities.identities = {"registered_local_identity": _identity}
        store = FileStore(name="s", path=str(tmp_path), identity="registered_local_identity")
        assert store.identity is _identity

    def test_platform_mismatch_raises_value_error(self, tmp_path):
        _aliyun_identity = AliyunIdentity(name="an_aliyun_identity")
        GlobalIdentities.identities = {"an_aliyun_identity": _aliyun_identity}
        with pytest.raises(ValueError):
            FileStore(name="s", path=str(tmp_path), identity="an_aliyun_identity")


class TestFileStoreDeriveDatabases:
    def test_eager_databases_empty_when_store_dir_is_empty(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        assert store.databases == []

    def test_eager_databases_populated_from_existing_subdirectories(self, tmp_path):
        (tmp_path / "db_a").mkdir()
        store = FileStore(name="s", path=str(tmp_path))
        assert [d.name for d in store.databases] == ["db_a"]

    def test_databases_property_is_already_cached_right_after_construction(self, monkeypatch, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        monkeypatch.setattr(FileStore, "list_databases", MagicMock())
        assert store.databases == []
        store.list_databases.assert_not_called()


class TestFileStoreFromSetting:
    def test_builds_store_from_setting_fields(self, tmp_path):
        _setting = FileStoreSetting(name="s", path=str(tmp_path), tags={"env": "prod"})
        store = FileStore.from_setting(_setting)
        assert store.name == "s"
        assert store.path == tmp_path
        assert store.tags["env"] == "prod"


class TestFileStoreListDatabases:
    def test_only_directories_are_listed_as_databases(self, tmp_path):
        (tmp_path / "db_a").mkdir()
        (tmp_path / "not_a_db.json").write_text("{}")
        store = FileStore(name="s", path=str(tmp_path))
        assert [d.name for d in store.list_databases()] == ["db_a"]

    def test_database_inherits_store_identity(self, tmp_path):
        (tmp_path / "db_a").mkdir()
        store = FileStore(name="s", path=str(tmp_path))
        assert store.list_databases()[0].identity is store.identity


class TestFileStoreDatabaseMethod:
    def test_creates_database_with_given_name_under_store_path(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        db = store.database("newdb")
        assert isinstance(db, FileStoreDatabase)
        assert db.path == tmp_path / "newdb"
        assert db.path.is_dir()

    def test_database_inherits_store_identity(self, tmp_path):
        store = FileStore(name="s", path=str(tmp_path))
        db = store.database("newdb")
        assert db.identity is store.identity

    @pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b", "a\\b"])
    def test_rejects_invalid_names(self, tmp_path, bad_name):
        store = FileStore(name="s", path=str(tmp_path))
        with pytest.raises(ValidationError):
            store.database(bad_name)
