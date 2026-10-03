from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.internal.constant.platform import Platform
from app.internal.constant.storesystem import StoreSystem
from app.resource.store._common._table import BaseTable


class _ConcreteTable(BaseTable):
    # BaseTable is abstract (write/read/delete); a trivial subclass exercises its shared logic.
    def write(self, key: str, data: Any, strict: bool = False) -> None:
        raise NotImplementedError

    def read(self, key: str, strict: bool = False) -> Any:
        raise NotImplementedError

    def delete(self, key: str, strict: bool = False) -> None:
        raise NotImplementedError


class _IncompleteTable(BaseTable):
    # Only implements two of the three abstract methods; must still fail to instantiate.
    def write(self, key: str, data: Any, strict: bool = False) -> None:
        raise NotImplementedError

    def read(self, key: str, strict: bool = False) -> Any:
        raise NotImplementedError


def _make_table(**overrides) -> _ConcreteTable:
    _kwargs = dict(name="tbl", storesystem=StoreSystem.FILE, platform=Platform.LOCAL, _authorized=True)
    _kwargs.update(overrides)
    return _ConcreteTable(**_kwargs)


class TestBaseTableGovernedConstruction:
    def test_cannot_instantiate_base_table_directly(self):
        with pytest.raises(TypeError):
            BaseTable(name="tbl", storesystem=StoreSystem.FILE, platform=Platform.LOCAL, _authorized=True)

    def test_subclass_missing_abstract_methods_cannot_instantiate(self):
        with pytest.raises(TypeError):
            _IncompleteTable(name="tbl", storesystem=StoreSystem.FILE, platform=Platform.LOCAL, _authorized=True)

    def test_missing_authorized_flag_raises_validation_error(self):
        with pytest.raises(ValidationError):
            _ConcreteTable(name="tbl", storesystem=StoreSystem.FILE, platform=Platform.LOCAL)

    def test_authorized_true_succeeds(self):
        table = _make_table()
        assert table.name == "tbl"

    @pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b", "a\\b"])
    def test_rejects_invalid_names(self, bad_name):
        with pytest.raises(ValidationError):
            _make_table(name=bad_name)


class TestBaseTableFrn:
    def test_frn_includes_platform_storesystem_and_name(self):
        table = _make_table(name="my_table")
        assert table.frn == "store:database:table:platform=local:storesystem=file:name=my_table"
