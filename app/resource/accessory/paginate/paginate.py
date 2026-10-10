from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from pydantic import Field, PrivateAttr, model_validator

from app.resource.accessory._common._base import BaseAccessory


class PaginatePage:
    """
    Page object representing a single page in the pagination sequence.

    Attributes:
    -----------
        offset (int):
            Read offset of this page, calculated as `size * number`.

    Args:
    -----------
        size (int):
            Number of items per page.
        number (int):
            Page number (0-indexed).

    """

    __slots__ = ("size", "number")

    def __init__(
        self,
        size: int,
        number: int,
    ) -> None:
        self.size = size
        self.number = number

    @property
    def offset(self) -> int:
        return self.size * self.number


class Paginate(BaseAccessory):
    """
    Page controller for managing pagination state.

    Attributes:
    -----------
        offset (int):
            Read offset of the next page, calculated as `page_size * current page`.
        is_exhausted (bool):
            Whether the current page has reached `end_page`.

    Args:
    -----------
        page_size (int):
            Page size (number of items per page).
        end_page (int | None):
            Exclusive upper bound of page numbers, default is None (unlimited).
        start_page (int):
            Starting page number (0-indexed), default is 0.

    Methods:
    -----------
        run() -> PaginatePage:
            Return the current page, then advance to the next one.
            Raises RuntimeError if `end_page` is reached.
        next() -> PaginatePage:
            Alias for `run()`.
        pages() -> Iterator[PaginatePage]:
            Yield pages until exhausted; never ends when `end_page` is None.
        reset() -> None:
            Move the internal page counter back to `start_page`.

    Notes:
    -----------
        Not thread-safe. `clone()` also copies the current page position.

    """

    # [Inherited] id: str
    # [Inherited] logstream: LogStream | None
    # [Inherited] tags: dict[str, str]
    page_size: int = Field(
        ...,
        description="number of items per page.",
        ge=1,  # page size must be at least 1
    )
    end_page: int | None = Field(
        default=None,
        description="end page number to fetch, default is None (unlimited).",
        ge=1,  # end_page must be at least 1 if specified
    )
    start_page: int = Field(
        default=0,
        description="start page number to fetch, must be >= 0 and < end_page if specified.",
        ge=0,  # start page must be non-negative and less than end_page if specified
    )

    # Private instance attributes
    _current_page: int = PrivateAttr(default=0)

    # Idempotent, so safe to re-run on validate_assignment.
    @model_validator(mode="after")
    def _check_page_range(self) -> Paginate:
        if self.end_page is not None and self.start_page >= self.end_page:
            raise ValueError("start_page must be less than end_page if specified")
        return self

    # Runs once at construction; a validator would reset progress on every assignment.
    def model_post_init(self, __context: Any) -> None:
        self._current_page = self.start_page

    @property
    def offset(self) -> int:
        return self.page_size * self._current_page

    @property
    def is_exhausted(self) -> bool:
        return self.end_page is not None and self._current_page >= self.end_page

    def run(self) -> PaginatePage:
        if self.is_exhausted:
            _msg = f"paginate exhausted after {self._current_page} pages"
            raise RuntimeError(_msg)

        _pageobj = PaginatePage(
            number=self._current_page,
            size=self.page_size,
        )
        self._current_page += 1
        self.debug(f"yield page {_pageobj.number} OK")
        return _pageobj

    def next(self) -> PaginatePage:
        return self.run()

    def pages(self) -> Iterator[PaginatePage]:
        while not self.is_exhausted:
            yield self.run()

    def reset(self) -> None:
        self._current_page = self.start_page
        self.debug("reset OK.")
