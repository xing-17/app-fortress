from __future__ import annotations

from unittest.mock import MagicMock

from app.internal.logstream.stream import LogStream
from app.resource.accessory._common._base import BaseAccessory


def _mock_logstream() -> MagicMock:
    return MagicMock(spec=LogStream)


class TestBaseAccessoryInit:
    def test_default_id_is_12_chars(self):
        accessory = BaseAccessory()
        assert isinstance(accessory.id, str)
        assert len(accessory.id) == 12

    def test_default_id_is_unique_per_instance(self):
        first = BaseAccessory()
        second = BaseAccessory()
        assert first.id != second.id

    def test_default_logstream_is_none(self):
        accessory = BaseAccessory()
        assert accessory.logstream is None

    def test_tags_default_factory_is_independent_per_instance(self):
        first = BaseAccessory()
        second = BaseAccessory()
        first.tags["env"] = "prod"
        assert "env" not in second.tags

    def test_explicit_fields_are_kept(self):
        accessory = BaseAccessory(id="fixed-id", tags={"env": "prod"})
        assert accessory.id == "fixed-id"
        assert accessory.tags == {"env": "prod"}


class TestBaseAccessoryKindAndFrn:
    def test_kind_returns_lowercased_class_name(self):
        accessory = BaseAccessory()
        assert accessory.kind == "baseaccessory"

    def test_frn_returns_kind_and_id(self):
        accessory = BaseAccessory(id="fixed-id")
        assert accessory.frn == "baseaccessory:id=fixed-id"


class TestBaseAccessoryLogging:
    def test_info_forwards_prefixed_message_to_logstream(self):
        logstream = _mock_logstream()
        accessory = BaseAccessory(id="fixed-id", logstream=logstream)
        accessory.info("hello", metadata={"a": 1}, metrics={"b": 2}, tags={"c": "d"})
        logstream.info.assert_called_once_with(
            msg="baseaccessory(fixed-id): hello",
            metadata={"a": 1},
            metrics={"b": 2},
            tags={"c": "d"},
        )

    def test_debug_forwards_prefixed_message_to_logstream(self):
        logstream = _mock_logstream()
        accessory = BaseAccessory(id="fixed-id", logstream=logstream)
        accessory.debug("hello")
        logstream.debug.assert_called_once_with(
            msg="baseaccessory(fixed-id): hello",
            metadata=None,
            metrics=None,
            tags=None,
        )

    def test_warning_forwards_prefixed_message_to_logstream(self):
        logstream = _mock_logstream()
        accessory = BaseAccessory(id="fixed-id", logstream=logstream)
        accessory.warning("hello")
        logstream.warning.assert_called_once_with(
            msg="baseaccessory(fixed-id): hello",
            metadata=None,
            metrics=None,
            tags=None,
        )

    def test_error_forwards_prefixed_message_to_logstream(self):
        logstream = _mock_logstream()
        accessory = BaseAccessory(id="fixed-id", logstream=logstream)
        accessory.error("hello")
        logstream.error.assert_called_once_with(
            msg="baseaccessory(fixed-id): hello",
            metadata=None,
            metrics=None,
            tags=None,
        )

    def test_critical_forwards_prefixed_message_to_logstream(self):
        logstream = _mock_logstream()
        accessory = BaseAccessory(id="fixed-id", logstream=logstream)
        accessory.critical("hello")
        logstream.critical.assert_called_once_with(
            msg="baseaccessory(fixed-id): hello",
            metadata=None,
            metrics=None,
            tags=None,
        )

    def test_logging_methods_are_no_op_without_logstream(self):
        accessory = BaseAccessory()
        assert accessory.info("hello") is None
        assert accessory.debug("hello") is None
        assert accessory.warning("hello") is None
        assert accessory.error("hello") is None
        assert accessory.critical("hello") is None


class TestBaseAccessoryExport:
    def test_export_includes_logstream_name_when_bound(self):
        logstream = _mock_logstream()
        logstream.name = "my_logstream"
        accessory = BaseAccessory(logstream=logstream)
        assert accessory.export()["logstream"] == "my_logstream"

    def test_export_logstream_is_none_when_unbound(self):
        accessory = BaseAccessory()
        assert accessory.export()["logstream"] is None
