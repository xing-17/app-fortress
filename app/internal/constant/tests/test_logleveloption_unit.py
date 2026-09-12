from __future__ import annotations

from enum import StrEnum

import pytest

from app.internal.constant.logleveloption import LogLevelOption


class TestLogLevelOptionValues:
    def test_debug_value(self):
        assert LogLevelOption.DEBUG == "DEBUG"

    def test_info_value(self):
        assert LogLevelOption.INFO == "INFO"

    def test_warning_value(self):
        assert LogLevelOption.WARNING == "WARNING"

    def test_error_value(self):
        assert LogLevelOption.ERROR == "ERROR"

    def test_members_count(self):
        assert len(LogLevelOption) == 4


class TestLogLevelOptionBehaviour:
    def test_is_str_enum(self):
        assert issubclass(LogLevelOption, StrEnum)

    def test_lookup_by_value(self):
        assert LogLevelOption("WARNING") is LogLevelOption.WARNING

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            LogLevelOption("invalid")
