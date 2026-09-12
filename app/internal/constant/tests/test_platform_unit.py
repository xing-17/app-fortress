from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.platform import Platform


class TestPlatformValues:
    def test_local_value(self):
        assert Platform.LOCAL == "local"

    def test_aliyun_value(self):
        assert Platform.ALIYUN == "aliyun"

    def test_members_count(self):
        assert len(Platform) == 2


class TestPlatformBehaviour:
    def test_is_str_enum(self):
        assert issubclass(Platform, StrEnum)

    def test_lookup_by_value(self):
        assert Platform("aliyun") is Platform.ALIYUN

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            Platform("invalid")
