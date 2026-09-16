from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.aliyunidentitytype import AliyunIdentityType


class TestAliyunIdentityTypeValues:
    def test_chain_value(self):
        assert AliyunIdentityType.CHAIN == "chain"

    def test_ak_value(self):
        assert AliyunIdentityType.AK == "ak"

    def test_members_count(self):
        assert len(AliyunIdentityType) == 2


class TestAliyunIdentityTypeBehaviour:
    def test_is_str_enum(self):
        assert issubclass(AliyunIdentityType, StrEnum)

    def test_lookup_by_value(self):
        assert AliyunIdentityType("chain") is AliyunIdentityType.CHAIN

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AliyunIdentityType("invalid")
