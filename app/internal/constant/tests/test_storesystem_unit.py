from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.storesystem import StoreSystem


class TestStoreSystemValues:
    def test_file_value(self):
        assert StoreSystem.FILE == "file"

    def test_oss_value(self):
        assert StoreSystem.OSS == "oss"

    def test_members_count(self):
        assert len(StoreSystem) == 2


class TestStoreSystemBehaviour:
    def test_is_str_enum(self):
        assert issubclass(StoreSystem, StrEnum)

    def test_lookup_by_value(self):
        assert StoreSystem("file") is StoreSystem.FILE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            StoreSystem("invalid")
