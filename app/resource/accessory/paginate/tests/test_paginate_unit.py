from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.internal.logstream.stream import LogStream
from app.resource.accessory.paginate.paginate import Paginate, PaginatePage


def _mock_logstream() -> MagicMock:
    return MagicMock(spec=LogStream)


class TestPaginatePage:
    def test_fields_are_kept(self):
        page = PaginatePage(size=10, number=3)
        assert page.size == 10
        assert page.number == 3

    def test_offset_is_size_times_number(self):
        assert PaginatePage(size=10, number=3).offset == 30

    def test_first_page_offset_is_zero(self):
        assert PaginatePage(size=10, number=0).offset == 0

    def test_has_no_instance_dict(self):
        assert not hasattr(PaginatePage(size=10, number=0), "__dict__")


class TestPaginateInit:
    def test_page_size_is_required(self):
        with pytest.raises(ValidationError):
            Paginate()

    def test_defaults(self):
        paginate = Paginate(page_size=10)
        assert paginate.end_page is None
        assert paginate.start_page == 0
        assert paginate.offset == 0
        assert paginate.is_exhausted is False

    def test_explicit_fields_are_kept(self):
        paginate = Paginate(page_size=20, start_page=2, end_page=5)
        assert paginate.page_size == 20
        assert paginate.start_page == 2
        assert paginate.end_page == 5
        assert paginate.offset == 40

    def test_page_size_below_one_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Paginate(page_size=0)

    def test_negative_start_page_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Paginate(page_size=10, start_page=-1)

    def test_end_page_below_one_raises_validation_error(self):
        with pytest.raises(ValidationError):
            Paginate(page_size=10, end_page=0)

    def test_start_page_equal_to_end_page_raises_validation_error(self):
        with pytest.raises(ValidationError, match="start_page must be less than end_page"):
            Paginate(page_size=10, start_page=3, end_page=3)

    def test_start_page_above_end_page_raises_validation_error(self):
        with pytest.raises(ValidationError, match="start_page must be less than end_page"):
            Paginate(page_size=10, start_page=5, end_page=3)


class TestPaginateOffset:
    def test_offset_starts_from_start_page(self):
        assert Paginate(page_size=10, start_page=5).offset == 50

    def test_offset_advances_after_run(self):
        paginate = Paginate(page_size=10)
        paginate.run()
        assert paginate.offset == 10


class TestPaginateIsExhausted:
    def test_never_exhausted_without_end_page(self):
        paginate = Paginate(page_size=10)
        for _ in range(50):
            paginate.run()
        assert paginate.is_exhausted is False

    def test_not_exhausted_before_end_page(self):
        paginate = Paginate(page_size=10, end_page=2)
        paginate.run()
        assert paginate.is_exhausted is False

    def test_exhausted_once_end_page_is_reached(self):
        paginate = Paginate(page_size=10, end_page=2)
        paginate.run()
        paginate.run()
        assert paginate.is_exhausted is True

    def test_end_page_is_an_absolute_exclusive_bound(self):
        paginate = Paginate(page_size=10, start_page=2, end_page=4)
        assert [p.number for p in paginate.pages()] == [2, 3]


class TestPaginateRun:
    def test_first_call_returns_start_page(self):
        page = Paginate(page_size=10).run()
        assert isinstance(page, PaginatePage)
        assert page.number == 0
        assert page.size == 10
        assert page.offset == 0

    def test_consecutive_calls_return_consecutive_pages(self):
        paginate = Paginate(page_size=10)
        assert [paginate.run().offset for _ in range(3)] == [0, 10, 20]

    def test_starts_from_start_page(self):
        page = Paginate(page_size=10, start_page=5).run()
        assert page.number == 5
        assert page.offset == 50

    def test_raises_runtime_error_when_exhausted(self):
        paginate = Paginate(page_size=10, end_page=1)
        paginate.run()
        with pytest.raises(RuntimeError, match="exhausted"):
            paginate.run()

    def test_exhausted_call_does_not_advance_page(self):
        paginate = Paginate(page_size=10, end_page=1)
        paginate.run()
        with pytest.raises(RuntimeError):
            paginate.run()
        assert paginate.offset == 10

    def test_logs_debug_message_with_returned_page_number(self):
        logstream = _mock_logstream()
        paginate = Paginate(page_size=10, logstream=logstream)
        paginate.run()
        logstream.debug.assert_called_once()
        assert "page 0" in logstream.debug.call_args.kwargs["msg"]

    def test_runs_without_logstream(self):
        assert Paginate(page_size=10, logstream=None).run().number == 0


class TestPaginateNext:
    def test_next_behaves_like_run(self):
        paginate = Paginate(page_size=10)
        page = paginate.next()
        assert page.number == 0
        assert paginate.offset == 10

    def test_next_raises_runtime_error_when_exhausted(self):
        paginate = Paginate(page_size=10, end_page=1)
        paginate.next()
        with pytest.raises(RuntimeError, match="exhausted"):
            paginate.next()


class TestPaginatePages:
    def test_yields_all_pages_up_to_end_page(self):
        paginate = Paginate(page_size=10, end_page=3)
        pages = list(paginate.pages())
        assert [p.number for p in pages] == [0, 1, 2]
        assert [p.offset for p in pages] == [0, 10, 20]

    def test_leaves_paginate_exhausted(self):
        paginate = Paginate(page_size=10, end_page=3)
        list(paginate.pages())
        assert paginate.is_exhausted is True

    def test_yields_nothing_when_already_exhausted(self):
        paginate = Paginate(page_size=10, end_page=1)
        paginate.run()
        assert list(paginate.pages()) == []

    def test_continues_from_current_position(self):
        paginate = Paginate(page_size=10, end_page=4)
        paginate.run()
        assert [p.number for p in paginate.pages()] == [1, 2, 3]

    def test_unbounded_pages_can_be_stopped_by_caller(self):
        paginate = Paginate(page_size=10)
        numbers = []
        for page in paginate.pages():
            numbers.append(page.number)
            if len(numbers) == 5:
                break
        assert numbers == [0, 1, 2, 3, 4]


class TestPaginateReset:
    def test_reset_goes_back_to_zero_by_default(self):
        paginate = Paginate(page_size=10)
        paginate.run()
        paginate.run()
        paginate.reset()
        assert paginate.offset == 0

    def test_reset_goes_back_to_start_page(self):
        paginate = Paginate(page_size=10, start_page=3)
        paginate.run()
        paginate.run()
        paginate.reset()
        assert paginate.offset == 30
        assert paginate.run().number == 3

    def test_reset_clears_exhausted_state(self):
        paginate = Paginate(page_size=10, end_page=1)
        paginate.run()
        paginate.reset()
        assert paginate.is_exhausted is False

    def test_reset_logs_debug_message(self):
        logstream = _mock_logstream()
        paginate = Paginate(page_size=10, logstream=logstream)
        paginate.reset()
        logstream.debug.assert_called_once()
        assert "reset OK" in logstream.debug.call_args.kwargs["msg"]


class TestPaginateAssignment:
    def test_assigning_unrelated_field_keeps_progress(self):
        paginate = Paginate(page_size=10)
        paginate.run()
        paginate.run()
        paginate.tags = {"k": "v"}
        assert paginate.offset == 20

    def test_assigning_invalid_range_raises_validation_error(self):
        paginate = Paginate(page_size=10, end_page=3)
        with pytest.raises(ValidationError):
            paginate.start_page = 3


class TestPaginateClone:
    def test_clone_copies_current_position(self):
        paginate = Paginate(page_size=10)
        paginate.run()
        assert paginate.clone().offset == 10

    def test_clone_progress_is_independent(self):
        paginate = Paginate(page_size=10)
        cloned = paginate.clone()
        cloned.run()
        assert paginate.offset == 0
        assert cloned.offset == 10

    def test_clone_of_fresh_instance_starts_at_start_page(self):
        assert Paginate(page_size=10, start_page=2).clone().offset == 20
