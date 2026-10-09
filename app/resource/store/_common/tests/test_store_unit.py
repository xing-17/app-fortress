from __future__ import annotations

from typing import ClassVar

import pytest

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource.store._common._database import BaseDatabase
from app.resource.store._common._store import BaseStore
from app.resource.store._common._table import BaseTable


class _ConcreteStore(BaseStore):
    # BaseStore is abstract (list_databases/database/table); a trivial subclass exercises its shared logic.
    storesystem: ClassVar[StoreSystem] = StoreSystem.FILE
    platform: ClassVar[Platform] = Platform.LOCAL

    def list_databases(self) -> list[BaseDatabase]:
        raise NotImplementedError

    def database(self, name: str) -> BaseDatabase:
        raise NotImplementedError

    def table(self, database: str, name: str, ttl_hours: float | None = None) -> BaseTable:
        raise NotImplementedError


class TestBaseStoreAbstractness:
    def test_cannot_instantiate_base_store_directly(self):
        with pytest.raises(TypeError):
            BaseStore(name="s")

    def test_concrete_subclass_is_instantiable(self):
        store = _ConcreteStore(name="s")
        assert store.name == "s"


class TestBaseStoreFrn:
    def test_frn_includes_platform_storesystem_and_name(self):
        store = _ConcreteStore(name="my_store")
        assert store.frn == "store:platform=local:storesystem=file:name=my_store"
