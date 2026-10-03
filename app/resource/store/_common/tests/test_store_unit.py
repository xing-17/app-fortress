from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource.store._common._database import BaseDatabase
from app.resource.store._common._store import BaseStore
from app.resource.store._common._table import BaseTable


class _ConcreteStore(BaseStore):
    # BaseStore is abstract (list_databases/database/table); a trivial subclass exercises its shared logic.
    def list_databases(self) -> list[BaseDatabase]:
        raise NotImplementedError

    def database(self, name: str) -> BaseDatabase:
        raise NotImplementedError

    def table(self, database: str, name: str) -> BaseTable:
        raise NotImplementedError


class TestBaseStoreAbstractness:
    def test_cannot_instantiate_base_store_directly(self):
        with pytest.raises(TypeError):
            BaseStore(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)

    def test_concrete_subclass_is_instantiable(self):
        store = _ConcreteStore(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        assert store.name == "s"


class TestBaseStoreFrn:
    def test_frn_includes_platform_storesystem_and_name(self):
        store = _ConcreteStore(name="my_store", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        assert store.frn == "store:platform=local:storesystem=file:name=my_store"


class TestBaseStoreDatabasesProperty:
    def test_first_access_calls_list_databases(self, monkeypatch):
        store = _ConcreteStore(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteStore, "list_databases", MagicMock(return_value=["db-a"]))
        assert store.databases == ["db-a"]
        store.list_databases.assert_called_once()

    def test_second_access_is_served_from_cache(self, monkeypatch):
        store = _ConcreteStore(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteStore, "list_databases", MagicMock(return_value=["db-a"]))
        first = store.databases
        second = store.databases
        assert first is second
        store.list_databases.assert_called_once()

    def test_empty_result_is_still_cached(self, monkeypatch):
        # regression: `not self._databases` would treat [] as "unset" and refetch every access
        store = _ConcreteStore(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteStore, "list_databases", MagicMock(return_value=[]))
        assert store.databases == []
        assert store.databases == []
        store.list_databases.assert_called_once()


class TestBaseStoreLoadDatabases:
    def test_force_true_always_refetches(self, monkeypatch):
        store = _ConcreteStore(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteStore, "list_databases", MagicMock(side_effect=[["db-a"], ["db-b"]]))
        first = store.load_databases()
        second = store.load_databases(force=True)
        assert first == ["db-a"]
        assert second == ["db-b"]
        assert store.list_databases.call_count == 2


class TestBaseStoreResetDatabases:
    def test_clears_cached_databases(self, monkeypatch):
        store = _ConcreteStore(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteStore, "list_databases", MagicMock(return_value=["db-a"]))
        store.load_databases()
        store.reset_databases()
        assert store._databases is None

    def test_next_access_refetches_after_reset(self, monkeypatch):
        store = _ConcreteStore(name="s", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)
        monkeypatch.setattr(_ConcreteStore, "list_databases", MagicMock(side_effect=[["db-a"], ["db-b"]]))
        store.load_databases()
        store.reset_databases()
        assert store.databases == ["db-b"]
