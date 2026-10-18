from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.internal.constant.logformatoption import LogFormatOption
from app.internal.constant.logleveloption import LogLevelOption
from app.setting import LogSetting, SystemLogSetting


class TestLogSetting:
    def test_defaults(self):
        _s = LogSetting()
        assert _s.name == "default"
        assert _s.level == LogLevelOption.INFO
        assert _s.console_verbose is True
        assert _s.console_format == LogFormatOption.TEXT
        assert _s.file_path is None
        assert _s.file_max_items is None
        assert _s.timezone is None
        assert _s.metadata is None

    def test_none_for_defaulted_field_falls_back_to_default(self):
        assert LogSetting(name=None).name == "default"

    def test_nullable_fields_keep_none(self):
        _s = LogSetting(level=None, console_format=None)
        assert _s.level is None
        assert _s.console_format is None

    def test_file_attributes(self):
        _s = LogSetting(file_path="./.log", file_max_items=10)
        assert _s.file_path == "./.log"
        assert _s.file_max_items == 10

    def test_file_max_items_must_be_int(self):
        with pytest.raises(ValidationError):
            LogSetting(file_max_items="many")

    def test_frn(self):
        assert LogSetting(name="x").frn == "setting:log:name=x"

    def test_timezone_in_tags_only_when_set(self):
        assert "timezone" not in LogSetting().tags
        assert LogSetting(timezone="UTC").tags["timezone"] == "UTC"

    def test_user_tags_cannot_override_reserved_tags(self):
        _s = LogSetting(name="x", timezone="UTC", tags={"name": "fake", "timezone": "fake", "env": "prod"})
        assert _s.tags["name"] == "x"
        assert _s.tags["timezone"] == "UTC"
        assert _s.tags["env"] == "prod"


class TestSystemLogSetting:
    def test_fixed_name_and_file_path(self):
        _s = SystemLogSetting()
        assert _s.name == "system"
        assert _s.file_path == "./.local/.logs/system"

    def test_name_cannot_be_changed(self):
        with pytest.raises(ValidationError):
            SystemLogSetting(name="other")

    def test_file_path_cannot_be_changed(self):
        with pytest.raises(ValidationError):
            SystemLogSetting(file_path="./other")

    def test_other_attributes_are_configurable(self):
        assert SystemLogSetting(level="DEBUG").level == LogLevelOption.DEBUG
