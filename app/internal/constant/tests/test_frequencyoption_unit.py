from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.frequencyoption import FrequencyOption


class TestFrequencyOptionValues:
    def test_second_value(self):
        assert FrequencyOption.SECOND == "SECOND"

    def test_minute_value(self):
        assert FrequencyOption.MINUTE == "MINUTE"

    def test_hour_value(self):
        assert FrequencyOption.HOUR == "HOUR"

    def test_day_value(self):
        assert FrequencyOption.DAY == "DAY"

    def test_week_value(self):
        assert FrequencyOption.WEEK == "WEEK"

    def test_month_value(self):
        assert FrequencyOption.MONTH == "MONTH"

    def test_quarter_value(self):
        assert FrequencyOption.QUARTER == "QUARTER"

    def test_year_value(self):
        assert FrequencyOption.YEAR == "YEAR"

    def test_members_count(self):
        assert len(FrequencyOption) == 8


class TestFrequencyOptionBehaviour:
    def test_is_str_enum(self):
        assert issubclass(FrequencyOption, StrEnum)

    def test_lookup_by_value(self):
        assert FrequencyOption("WEEK") is FrequencyOption.WEEK

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            FrequencyOption("invalid")
