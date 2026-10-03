from __future__ import annotations

import pytest

from app.internal.util.frn import IFrn


class TestIFrnResolve:
    def test_joins_values_with_colon(self):
        assert IFrn.resolve(["frn", "fortress", "asset", "local"]) == "frn:fortress:asset:local"

    def test_empty_list_returns_empty_string(self):
        assert IFrn.resolve([]) == ""

    def test_falsy_items_are_filtered_out(self):
        assert IFrn.resolve(["frn", "", "asset", None]) == "frn:asset"  # type: ignore[list-item]

    def test_all_falsy_items_returns_empty_string(self):
        assert IFrn.resolve(["", None, ""]) == ""  # type: ignore[list-item]

    def test_single_item_returns_item_unchanged(self):
        assert IFrn.resolve(["frn"]) == "frn"

    def test_order_is_preserved(self):
        assert IFrn.resolve(["b", "a", "c"]) == "b:a:c"


class TestIFrnInit:
    def test_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            IFrn()
