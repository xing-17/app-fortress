from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.geocountry import GeoCountry


class TestGeoCountryValues:
    def test_cn_value(self):
        assert GeoCountry.CN == "CN"

    def test_au_value(self):
        assert GeoCountry.AU == "AU"

    def test_global_value(self):
        assert GeoCountry.GLOBAL == "GLOBAL"

    def test_members_count(self):
        assert len(GeoCountry) == 3


class TestGeoCountryBehaviour:
    def test_is_str_enum(self):
        assert issubclass(GeoCountry, StrEnum)

    def test_lookup_by_value(self):
        assert GeoCountry("CN") is GeoCountry.CN

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            GeoCountry("invalid")
