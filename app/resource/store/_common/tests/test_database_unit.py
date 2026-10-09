from __future__ import annotations

from typing import ClassVar

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource.store._common._database import BaseDatabase
from app.resource.store._common._table import BaseTable


class _ConcreteDatabase(BaseDatabase):
    # BaseDatabase is abstract (frn/list_tables/table/delete); a trivial subclass exercises its shared logic.
    storesystem: ClassVar[StoreSystem] = StoreSystem.FILE
    platform: ClassVar[Platform] = Platform.LOCAL

    @property
    def frn(self) -> str:
        return f"concrete:database:{self.name}"

    def list_tables(self) -> list[BaseTable]:
        raise NotImplementedError

    def table(self, name: str, ttl_hours: float | None = None) -> BaseTable:
        raise NotImplementedError

    def delete(self, name: str, strict: bool = False) -> None:
        raise NotImplementedError


def _make_database(**overrides) -> _ConcreteDatabase:
    _kwargs = dict(name="db", _authorized=True)
    _kwargs.update(overrides)
    return _ConcreteDatabase(**_kwargs)


class TestBaseDatabaseGovernedConstruction:
    def test_cannot_instantiate_base_database_directly(self):
        with pytest.raises(TypeError):
            BaseDatabase(name="db", _authorized=True)

    def test_missing_authorized_flag_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteDatabase(name="db")

    def test_authorized_true_succeeds(self):
        database = _make_database()
        assert database.name == "db"

    @pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b", "a\\b"])
    def test_rejects_invalid_names(self, bad_name):
        with pytest.raises(ValidationError):
            _make_database(name=bad_name)


class TestBaseDatabaseFrn:
    def test_frn_is_abstract_and_supplied_by_subclass(self):
        database = _make_database(name="my_db")
        assert database.frn == "concrete:database:my_db"
