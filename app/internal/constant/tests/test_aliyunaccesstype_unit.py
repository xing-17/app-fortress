from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.aliyunaccesstype import AliyunAccessType


class TestAliyunAccessTypeValues:
    def test_chain_value(self):
        assert AliyunAccessType.CHAIN == "chain"

    def test_ak_value(self):
        assert AliyunAccessType.AK == "ak"

    def test_members_count(self):
        assert len(AliyunAccessType) == 2


class TestAliyunAccessTypeBehaviour:
    def test_is_str_enum(self):
        assert issubclass(AliyunAccessType, StrEnum)

    def test_lookup_by_value(self):
        assert AliyunAccessType("chain") is AliyunAccessType.CHAIN

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AliyunAccessType("invalid")
