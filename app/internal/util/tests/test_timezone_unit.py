from __future__ import annotations

from zoneinfo import ZoneInfo

import pytest

from app.internal.util.timezone import ITimezone


class TestITimezoneResolve:
    def test_resolve_none_returns_default(self):
        assert ITimezone.resolve(None) is ITimezone.default

    def test_resolve_zoneinfo_returns_same_instance(self):
        tz = ZoneInfo("Australia/Sydney")
        assert ITimezone.resolve(tz) is tz

    def test_resolve_valid_string_returns_zoneinfo(self):
        result = ITimezone.resolve("Australia/Sydney")
        assert result == ZoneInfo("Australia/Sydney")

    def test_resolve_invalid_string_returns_default(self):
        assert ITimezone.resolve("Not/AValidZone") is ITimezone.default

    def test_resolve_invalid_type_raises_type_error(self):
        with pytest.raises(TypeError):
            ITimezone.resolve(123)  # type: ignore[arg-type]
