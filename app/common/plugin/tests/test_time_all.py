"""
综合测试：app.common.plugin.time

覆盖范围
--------
- TestTimezone       _time_zoneinfo 时区解析与无效时区 UTC 回退
- TestGetters        各时间获取方法的返回值类型
- TestTimezoneAware  datetime 携带正确时区信息
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.common.core.setting import GlobalSetting
from app.common.plugin.time import TimePlugin

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


class _Task(TimePlugin):
    pass


# ──────────────────────────────────────────────────────────────────────────────
# TestTimezone
# ──────────────────────────────────────────────────────────────────────────────


class TestTimezone:
    def test_time_zoneinfo_returns_zoneinfo_instance(self):
        task = _Task()
        assert isinstance(task._time_zoneinfo, ZoneInfo)

    def test_time_zoneinfo_matches_global_setting(self):
        task = _Task()
        expected = ZoneInfo(GlobalSetting.system.timezone)
        assert task._time_zoneinfo == expected

    def test_invalid_timezone_falls_back_to_utc(self, monkeypatch):
        monkeypatch.setattr(GlobalSetting.system, "timezone", "Invalid/Zone")
        task = _Task()
        assert task._time_zoneinfo == ZoneInfo("UTC")


# ──────────────────────────────────────────────────────────────────────────────
# TestGetters
# ──────────────────────────────────────────────────────────────────────────────


class TestGetters:
    def test_get_current_timestamp_returns_float(self):
        task = _Task()
        result = task._get_current_timestamp()
        assert isinstance(result, float)

    def test_get_current_timestamp_is_numeric(self):
        task = _Task()
        result = task._get_current_timestamp()
        assert isinstance(result, float)

    def test_get_current_timestamp_length_is_10(self):
        task = _Task()
        result = task._get_current_timestamp()
        assert len(str(int(result))) == 10

    def test_get_current_datetime_returns_datetime(self):
        task = _Task()
        result = task._get_current_datetime()
        assert isinstance(result, datetime)

    def test_get_current_date_returns_date(self):
        task = _Task()
        result = task._get_current_date()
        assert isinstance(result, date)

    def test_get_current_date_is_not_datetime(self):
        task = _Task()
        result = task._get_current_date()
        # date, not datetime (datetime is a subclass of date, so check exactly)
        assert type(result) is date


# ──────────────────────────────────────────────────────────────────────────────
# TestTimezoneAware
# ──────────────────────────────────────────────────────────────────────────────


class TestTimezoneAware:
    def test_datetime_is_timezone_aware(self):
        task = _Task()
        dt = task._get_current_datetime()
        assert dt.tzinfo is not None

    def test_datetime_timezone_key_matches_setting(self):
        task = _Task()
        dt = task._get_current_datetime()
        expected_key = GlobalSetting.system.timezone
        assert dt.tzinfo.key == expected_key

    def test_successive_timestamps_are_non_decreasing(self):
        task = _Task()
        t1 = int(task._get_current_timestamp())
        t2 = int(task._get_current_timestamp())
        assert t2 >= t1
