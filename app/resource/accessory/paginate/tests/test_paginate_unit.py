from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.logstream.stream import LogStream
from app.resource.accessory.paginate.paginate import Paginate


def _mock_logstream() -> MagicMock:
    return MagicMock(spec=LogStream)


class TestPaginateInit:
    def test_page_size_is_required(self):
        with pytest.raises(ValidationError):
            Paginate()

    def test_defaults(self):
        paginate = Paginate(page_size=10)
        assert paginate.max_pages is None
        assert paginate.offset == 0
        assert paginate.raise_on_exhausted is False

    def test_explicit_fields_are_kept(self):
        paginate = Paginate(page_size=20, max_pages=3, offset=40, raise_on_exhausted=True)
        assert paginate.page_size == 20
        assert paginate.max_pages == 3
        assert paginate.offset == 40
        assert paginate.raise_on_exhausted is True

    def test_page_size_below_one_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Paginate(page_size=0)

    def test_negative_offset_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Paginate(page_size=10, offset=-1)


class TestPaginateRun:
    def test_first_call_returns_zero_and_advances_offset(self):
        paginate = Paginate(page_size=10)
        assert paginate.run() == 0
        assert paginate.offset == 10

    def test_second_call_returns_previous_offset_and_advances_again(self):
        paginate = Paginate(page_size=10)
        paginate.run()
        assert paginate.run() == 10
        assert paginate.offset == 20

    def test_starts_from_explicit_offset(self):
        paginate = Paginate(page_size=10, offset=50)
        assert paginate.run() == 50
        assert paginate.offset == 60

    def test_exhausted_raises_runtime_error_when_raise_on_exhausted_true(self):
        paginate = Paginate(page_size=10, max_pages=1, raise_on_exhausted=True)
        paginate.run()
        with pytest.raises(RuntimeError, match="exhausted"):
            paginate.run()

    def test_exhausted_returns_offset_unchanged_when_raise_on_exhausted_false(self):
        paginate = Paginate(page_size=10, max_pages=1, raise_on_exhausted=False)
        paginate.run()
        assert paginate.run() == 10
        assert paginate.offset == 10

    def test_exhausted_logs_warning(self):
        logstream = _mock_logstream()
        paginate = Paginate(page_size=10, max_pages=1, raise_on_exhausted=False, logstream=logstream)
        paginate.run()
        paginate.run()
        logstream.warning.assert_called_once()

    def test_logs_debug_message_with_page_number(self):
        logstream = _mock_logstream()
        paginate = Paginate(page_size=10, logstream=logstream)
        paginate.run()
        logstream.debug.assert_called_once()
        assert "page 1" in logstream.debug.call_args.kwargs["msg"]


class TestPaginateNext:
    def test_next_behaves_like_run(self):
        paginate = Paginate(page_size=10)
        assert paginate.next() == 0
        assert paginate.offset == 10


class TestPaginateReset:
    def test_reset_sets_offset_and_page_back_to_zero(self):
        paginate = Paginate(page_size=10)
        paginate.run()
        paginate.run()
        paginate.reset()
        assert paginate.offset == 0
        assert paginate._page == 0

    def test_reset_logs_debug_message(self):
        logstream = _mock_logstream()
        paginate = Paginate(page_size=10, logstream=logstream)
        paginate.reset()
        logstream.debug.assert_called_once()
        assert "reset OK" in logstream.debug.call_args.kwargs["msg"]
