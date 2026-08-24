"""Unit tests for IClock."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from bastion.internal.iclock import IClock


def test_from_iso_valid():
    """Test converting a valid ISO 8601 string to datetime."""
    iso_str = "2026-08-14T10:30:00+00:00"
    result = IClock.from_iso(iso_str)
    assert result is not None
    assert result.tzinfo == ZoneInfo("UTC")
    assert result.year == 2026
    assert result.month == 8
    assert result.day == 14


def test_from_iso_empty():
    """Test converting an empty string returns None."""
    result = IClock.from_iso("")
    assert result is None


def test_from_timestamp():
    """Test converting a POSIX timestamp to datetime."""
    timestamp = 1723633800.0  # 2024-08-14 10:30:00 UTC
    result = IClock.from_timestamp(timestamp)
    assert result.tzinfo == ZoneInfo("UTC")
    assert isinstance(result, datetime)


def test_current():
    """Test getting the current UTC datetime."""
    result = IClock.current()
    assert result.tzinfo == ZoneInfo("UTC")
    assert isinstance(result, datetime)


def test_current_iso():
    """Test getting the current UTC time as ISO string."""
    result = IClock.current_iso()
    assert isinstance(result, str)
    assert "T" in result
    # Verify it can be parsed back
    parsed = IClock.from_iso(result)
    assert parsed is not None


def test_current_timestamp():
    """Test getting the current UTC time as timestamp."""
    result = IClock.current_timestamp()
    assert isinstance(result, float)
    assert result > 0
