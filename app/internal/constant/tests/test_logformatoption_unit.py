from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.logformatoption import LogFormatOption


class TestLogFormatOptionValues:
    def test_text_value(self):
        assert LogFormatOption.TEXT == "TEXT"

    def test_colortext_value(self):
        assert LogFormatOption.COLORTEXT == "COLORTEXT"

    def test_tree_value(self):
        assert LogFormatOption.TREE == "TREE"

    def test_colortree_value(self):
        assert LogFormatOption.COLORTREE == "COLORTREE"

    def test_members_count(self):
        assert len(LogFormatOption) == 4


class TestLogFormatOptionBehaviour:
    def test_is_str_enum(self):
        assert issubclass(LogFormatOption, StrEnum)

    def test_lookup_by_value(self):
        assert LogFormatOption("TREE") is LogFormatOption.TREE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            LogFormatOption("invalid")
