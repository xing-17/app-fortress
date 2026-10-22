from __future__ import annotations

import pytest

from app.service.node.dra.errors import (
    DRABusyError,
    DRAError,
    DRAQueryError,
    DRAQueryTimeoutError,
    DRARejectedError,
)


@pytest.mark.parametrize(
    "error_cls",
    [DRARejectedError, DRAQueryTimeoutError, DRAQueryError, DRABusyError],
)
class TestDRAErrorHierarchy:
    def test_is_subclass_of_base(self, error_cls):
        assert issubclass(error_cls, DRAError)

    def test_can_be_caught_as_base(self, error_cls):
        with pytest.raises(DRAError):
            raise error_cls("boom")

    def test_message_is_kept(self, error_cls):
        assert str(error_cls("boom")) == "boom"


def test_base_is_plain_exception():
    assert issubclass(DRAError, Exception)


def test_siblings_are_distinct():
    with pytest.raises(DRAQueryTimeoutError):
        try:
            raise DRAQueryTimeoutError("t")
        except DRAQueryError:
            pytest.fail("timeout must not be caught as query error")
