from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource.store._common._database import BaseDatabase
from app.resource.store._common._table import BaseTable


class _ConcreteDatabase(BaseDatabase):
    # BaseDatabase is abstract (list_tables/table/delete); a trivial subclass exercises its shared logic.
    def list_tables(self) -> list[BaseTable]:
        raise NotImplementedError

    def table(self, name: str) -> BaseTable:
        raise NotImplementedError

    def delete(self, name: str, strict: bool = False) -> None:
        raise NotImplementedError


def _make_database(**overrides) -> _ConcreteDatabase:
    _kwargs = dict(name="db", storesystem=StoreSystem.FILE, platform=Platform.LOCAL, _authorized=True)
    _kwargs.update(overrides)
    return _ConcreteDatabase(**_kwargs)


class TestBaseDatabaseGovernedConstruction:
    def test_cannot_instantiate_base_database_directly(self):
        with pytest.raises(TypeError):
            BaseDatabase(name="db", storesystem=StoreSystem.FILE, platform=Platform.LOCAL, _authorized=True)

    def test_missing_authorized_flag_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteDatabase(name="db", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)

    def test_authorized_true_succeeds(self):
        database = _make_database()
        assert database.name == "db"

    @pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b", "a\\b"])
    def test_rejects_invalid_names(self, bad_name):
        with pytest.raises(ValidationError):
            _make_database(name=bad_name)


class TestBaseDatabaseFrn:
    def test_frn_includes_platform_storesystem_and_name(self):
        database = _make_database(name="my_db")
        assert database.frn == "store:database:platform=local:storesystem=file:name=my_db"


class TestBaseDatabaseTablesProperty:
    def test_first_access_calls_list_tables(self, monkeypatch):
        database = _make_database()
        monkeypatch.setattr(_ConcreteDatabase, "list_tables", MagicMock(return_value=["tbl-a"]))
        assert database.tables == ["tbl-a"]
        database.list_tables.assert_called_once()

    def test_second_access_is_served_from_cache(self, monkeypatch):
        database = _make_database()
        monkeypatch.setattr(_ConcreteDatabase, "list_tables", MagicMock(return_value=["tbl-a"]))
        first = database.tables
        second = database.tables
        assert first is second
        database.list_tables.assert_called_once()

    def test_empty_result_is_still_cached(self, monkeypatch):
        # regression: `not self._tables` would treat [] as "unset" and refetch every access
        database = _make_database()
        monkeypatch.setattr(_ConcreteDatabase, "list_tables", MagicMock(return_value=[]))
        assert database.tables == []
        assert database.tables == []
        database.list_tables.assert_called_once()


class TestBaseDatabaseLoadTables:
    def test_force_true_always_refetches(self, monkeypatch):
        database = _make_database()
        monkeypatch.setattr(_ConcreteDatabase, "list_tables", MagicMock(side_effect=[["tbl-a"], ["tbl-b"]]))
        first = database.load_tables()
        second = database.load_tables(force=True)
        assert first == ["tbl-a"]
        assert second == ["tbl-b"]
        assert database.list_tables.call_count == 2


class TestBaseDatabaseResetTables:
    def test_clears_cached_tables(self, monkeypatch):
        database = _make_database()
        monkeypatch.setattr(_ConcreteDatabase, "list_tables", MagicMock(return_value=["tbl-a"]))
        database.load_tables()
        database.reset_tables()
        assert database._tables is None
