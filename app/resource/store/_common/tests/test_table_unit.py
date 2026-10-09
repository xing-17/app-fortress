from __future__ import annotations

from typing import Any, ClassVar

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource.store._common._table import BaseTable


class _ConcreteTable(BaseTable):
    # BaseTable is abstract (frn/write/read/delete/expire); a trivial subclass exercises its shared logic.
    storesystem: ClassVar[StoreSystem] = StoreSystem.FILE
    platform: ClassVar[Platform] = Platform.LOCAL

    @property
    def frn(self) -> str:
        return f"concrete:table:{self.name}"

    def write(self, key: str, data: Any, strict: bool = False) -> None:
        raise NotImplementedError

    def read(self, key: str, strict: bool = False) -> Any:
        raise NotImplementedError

    def delete(self, key: str, strict: bool = False) -> None:
        raise NotImplementedError

    def expire(self) -> None:
        raise NotImplementedError


class _IncompleteTable(BaseTable):
    # Only implements two of the abstract methods; must still fail to instantiate.
    storesystem: ClassVar[StoreSystem] = StoreSystem.FILE
    platform: ClassVar[Platform] = Platform.LOCAL

    @property
    def frn(self) -> str:
        return "incomplete:table"

    def write(self, key: str, data: Any, strict: bool = False) -> None:
        raise NotImplementedError

    def read(self, key: str, strict: bool = False) -> Any:
        raise NotImplementedError


def _make_table(**overrides) -> _ConcreteTable:
    _kwargs = dict(name="tbl", _authorized=True)
    _kwargs.update(overrides)
    return _ConcreteTable(**_kwargs)


class TestBaseTableGovernedConstruction:
    def test_cannot_instantiate_base_table_directly(self):
        with pytest.raises(TypeError):
            BaseTable(name="tbl", _authorized=True)

    def test_subclass_missing_abstract_methods_cannot_instantiate(self):
        with pytest.raises(TypeError):
            _IncompleteTable(name="tbl", _authorized=True)

    def test_missing_authorized_flag_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteTable(name="tbl")

    def test_authorized_true_succeeds(self):
        table = _make_table()
        assert table.name == "tbl"

    @pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b", "a\\b"])
    def test_rejects_invalid_names(self, bad_name):
        with pytest.raises(ValidationError):
            _make_table(name=bad_name)


class TestBaseTableFrn:
    def test_frn_is_abstract_and_supplied_by_subclass(self):
        table = _make_table(name="my_table")
        assert table.frn == "concrete:table:my_table"


class TestBaseTableTtlHours:
    def test_default_is_none(self):
        assert _make_table().ttl_hours is None

    def test_positive_value_is_accepted(self):
        assert _make_table(ttl_hours=0.5).ttl_hours == 0.5

    @pytest.mark.parametrize("bad_ttl", [0, 0.0, -1, -0.5])
    def test_non_positive_value_raises_validation_error(self, bad_ttl):
        with pytest.raises(ValidationError):
            _make_table(ttl_hours=bad_ttl)
