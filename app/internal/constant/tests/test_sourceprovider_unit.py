from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.sourceprovider import SourceProvider, SourceProviderType


class TestSourceProviderValues:
    def test_tushare_value(self):
        assert SourceProvider.TUSHARE == "tushare"

    def test_abs_value(self):
        assert SourceProvider.ABS == "abs"

class TestSourceProviderBehaviour:
    def test_is_str_enum(self):
        assert issubclass(SourceProvider, StrEnum)

    def test_lookup_by_value(self):
        assert SourceProvider("tushare") is SourceProvider.TUSHARE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            SourceProvider("invalid")


class TestSourceProviderTypeValues:
    def test_org_value(self):
        assert SourceProviderType.ORG == "org"

    def test_gov_value(self):
        assert SourceProviderType.GOV == "gov"

    def test_members_count(self):
        assert len(SourceProviderType) == 2


class TestSourceProviderTypeBehaviour:
    def test_is_str_enum(self):
        assert issubclass(SourceProviderType, StrEnum)

    def test_lookup_by_value(self):
        assert SourceProviderType("org") is SourceProviderType.ORG

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            SourceProviderType("invalid")
