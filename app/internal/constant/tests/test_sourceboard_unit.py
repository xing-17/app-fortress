from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.sourceboard import SourceBoard


class TestSourceBoardValues:
    def test_finance_value(self):
        assert SourceBoard.FINANCE == "finance"

    def test_macro_value(self):
        assert SourceBoard.MACRO == "macro"

    def test_members_count(self):
        assert len(SourceBoard) == 2


class TestSourceBoardBehaviour:
    def test_is_str_enum(self):
        assert issubclass(SourceBoard, StrEnum)

    def test_lookup_by_value(self):
        assert SourceBoard("finance") is SourceBoard.FINANCE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            SourceBoard("invalid")
