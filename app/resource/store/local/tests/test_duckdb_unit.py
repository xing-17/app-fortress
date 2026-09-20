from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.resource._global.identities import GlobalIdentities
from app.resource.identity.local import LocalIdentity
from app.resource.store.local import duckdb as duckdb_module
from app.resource.store.local.duckdb import DuckDbStore
from app.setting._store import LocalStoreSetting


@pytest.fixture(autouse=True)
def _reset_global_identities():
    # GlobalIdentities holds process-wide singleton state; isolate tests from each other.
    GlobalIdentities.reset()
    yield
    GlobalIdentities.reset()


class TestDuckDbStoreInit:
    def test_missing_required_fields_raises_validation_error(self):
        with pytest.raises(ValidationError):
            DuckDbStore()

    def test_platform_is_fixed_to_local(self, tmp_path):
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path))
        assert store.platform == Platform.LOCAL

    def test_default_identity_is_local_default(self, tmp_path):
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path))
        assert store.identity.name == LocalIdentity.default().name

    def test_default_tags_is_empty_dict(self, tmp_path):
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path))
        assert store.tags == {}


class TestDuckDbStoreDerivePath:
    def test_invalid_name_raises_validation_error(self, tmp_path):
        with pytest.raises(ValidationError):
            DuckDbStore(name="bad name!", path=str(tmp_path))

    def test_explicit_path_is_resolved(self, tmp_path):
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path))
        assert store._path == tmp_path.expanduser().resolve()

    def test_file_is_name_with_db_suffix(self, tmp_path):
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path))
        assert store._file == tmp_path.expanduser().resolve() / "my-duckdb-store.db"

    def test_default_path_is_used_when_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = DuckDbStore(name="my-duckdb-store")
        assert store._path == (tmp_path / ".store" / "local").expanduser().resolve()


class TestDuckDbStoreFromSetting:
    def test_from_setting_copies_basic_fields(self, tmp_path):
        setting = LocalStoreSetting(
            name="my-duckdb-store",
            path=str(tmp_path),
            config={"memory_limit": "1GB"},
            tags={"env": "test"},
        )
        store = DuckDbStore.from_setting(setting)
        assert store.name == "my-duckdb-store"
        assert store.path == str(tmp_path)
        assert store.config == {"memory_limit": "1GB"}

    def test_from_setting_resolves_registered_identity(self, tmp_path):
        identity = LocalIdentity(name="my-identity")
        GlobalIdentities.identities = {"my-identity": identity}
        setting = LocalStoreSetting(
            name="my-duckdb-store",
            path=str(tmp_path),
            identity="my-identity",
            tags={},
        )
        store = DuckDbStore.from_setting(setting)
        assert store.identity is identity

    def test_from_setting_falls_back_to_default_identity_when_not_registered(self, tmp_path):
        GlobalIdentities.identities = {}
        setting = LocalStoreSetting(
            name="my-duckdb-store",
            path=str(tmp_path),
            identity="missing-identity",
            tags={},
        )
        store = DuckDbStore.from_setting(setting)
        assert store.identity.name == LocalIdentity.default().name

    def test_from_setting_returns_duckdb_store_instance(self, tmp_path):
        setting = LocalStoreSetting(
            name="my-duckdb-store",
            path=str(tmp_path),
            tags={},
        )
        store = DuckDbStore.from_setting(setting)
        assert isinstance(store, DuckDbStore)


class TestDuckDbStoreConn:
    def test_conn_is_built_via_duckdb_connect(self, tmp_path, monkeypatch):
        _mock_connect = MagicMock()
        monkeypatch.setattr(duckdb_module.duckdb, "connect", _mock_connect)
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path))

        result = store.conn

        _mock_connect.assert_called_once_with(
            database=str(store._file),
            read_only=False,
            config=None,
        )
        assert result is _mock_connect.return_value

    def test_conn_is_cached_across_calls(self, tmp_path, monkeypatch):
        _mock_connect = MagicMock()
        monkeypatch.setattr(duckdb_module.duckdb, "connect", _mock_connect)
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path))

        first = store.conn
        second = store.conn

        assert first is second
        _mock_connect.assert_called_once()

    def test_conn_passes_provided_config(self, tmp_path, monkeypatch):
        _mock_connect = MagicMock()
        monkeypatch.setattr(duckdb_module.duckdb, "connect", _mock_connect)
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path), config={"memory_limit": "1GB"})

        store.conn

        _mock_connect.assert_called_once_with(
            database=str(store._file),
            read_only=False,
            config={"memory_limit": "1GB"},
        )


class TestDuckDbStoreClose:
    def test_close_closes_active_connection(self, tmp_path):
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path))
        _mock_conn = MagicMock()
        store._conn = _mock_conn

        store.close()

        _mock_conn.close.assert_called_once()
        assert store._conn is None

    def test_close_is_noop_when_no_connection(self, tmp_path):
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path))
        store.close()
        assert store._conn is None

    def test_context_manager_closes_connection_on_exit(self, tmp_path):
        _mock_conn = MagicMock()
        with DuckDbStore(name="my-duckdb-store", path=str(tmp_path)) as store:
            store._conn = _mock_conn

        _mock_conn.close.assert_called_once()
        assert store._conn is None


class TestDuckDbStoreExport:
    def test_export_replaces_identity_with_name(self, tmp_path):
        identity = LocalIdentity(name="my-identity")
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path), identity=identity)
        result = store.export()
        assert result["identity"] == "my-identity"

    def test_describe_is_valid_json_containing_identity_name(self, tmp_path):
        identity = LocalIdentity(name="my-identity")
        store = DuckDbStore(name="my-duckdb-store", path=str(tmp_path), identity=identity)
        result = json.loads(store.describe())
        assert result["identity"] == "my-identity"
