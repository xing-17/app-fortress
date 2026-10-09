from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.internal.util.clock import IClock


class TestIClockCurrent:
    def test_current_default_timezone_is_utc(self):
        result = IClock.current()
        assert result.tzinfo == ZoneInfo("UTC")

    def test_current_with_timezone_string(self):
        result = IClock.current("Australia/Sydney")
        assert result.tzinfo == ZoneInfo("Australia/Sydney")

    def test_current_iso_returns_isoformat_string(self):
        result = IClock.current_iso("UTC")
        assert result == IClock.from_iso(result, "UTC").isoformat()

    def test_current_timestamp_is_float(self):
        result = IClock.current_timestamp()
        assert isinstance(result, float)

    def test_current_with_zoneinfo_instance(self):
        tz = ZoneInfo("Asia/Shanghai")
        result = IClock.current(tz)
        assert result.tzinfo == tz


class TestIClockCurrentSnapshotdate:
    def test_current_snapshotdate_returns_date_string(self):
        result = IClock.current_snapshotdate("UTC")
        assert result == IClock.current("UTC").strftime("%Y-%m-%d")

    def test_current_snapshotdate_default_timezone_is_utc(self):
        result = IClock.current_snapshotdate()
        assert result == IClock.current().strftime("%Y-%m-%d")


class TestIClockFromDatetime:
    def test_from_naive_datetime_attaches_timezone(self):
        naive = datetime(2024, 1, 1, 12, 0, 0)
        result = IClock.from_datetime(naive, "UTC")
        assert result.tzinfo == ZoneInfo("UTC")
        assert result.replace(tzinfo=None) == naive

    def test_from_aware_datetime_converts_timezone(self):
        aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        result = IClock.from_datetime(aware, "Australia/Sydney")
        assert result.tzinfo == ZoneInfo("Australia/Sydney")
        assert result == aware


class TestIClockFromIso:
    def test_from_iso_parses_and_applies_timezone(self):
        result = IClock.from_iso("2024-01-01T12:00:00", "UTC")
        assert result == datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

    def test_from_iso_with_offset_converts_to_target_timezone(self):
        result = IClock.from_iso("2024-01-01T12:00:00+00:00", "Australia/Sydney")
        assert result.tzinfo == ZoneInfo("Australia/Sydney")
        assert result == datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))


class TestIClockFromTimestamp:
    def test_from_timestamp_returns_aware_datetime(self):
        result = IClock.from_timestamp(0, "UTC")
        assert result == datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))

    def test_from_timestamp_default_timezone_is_utc(self):
        result = IClock.from_timestamp(0)
        assert result.tzinfo == ZoneInfo("UTC")
