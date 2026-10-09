from __future__ import annotations

from pydantic import Field, PrivateAttr

from app.resource.accessory._common._base import BaseAccessory


class Paginate(BaseAccessory):
    """
    Page controller for managing pagination state.

    Args:
    -----------
        page_size (int):
            Page size (number of items per page).
        max_pages (int | None):
            Maximum number of pages to fetch, default is None (unlimited).
        offset (int):
            Current read offset.
        raise_on_exhausted (bool):
            Whether to raise an exception when pagination is exhausted.

    Methods:
    -----------
        run() -> int:
            Return the current offset, then advance it by `page_size`.
            Raises StopIteration if `max_pages` is reached and `raise_on_exhausted` is True.
        next() -> int:
            Alias for `run()`.
        reset() -> None:
            Reset `offset` and the internal page counter back to 0.

    """

    # [Inherited] id: str
    # [Inherited] logstream: LogStream | None
    # [Inherited] tags: dict[str, str]
    page_size: int = Field(
        ...,
        description="page size (number of items per page).",
        ge=1,  # page size must be at least 1
    )
    max_pages: int | None = Field(
        default=None,
        description="maximum number of pages to fetch, default is None.",
    )
    offset: int = Field(
        default=0,
        description="current read offset.",
        ge=0,  # offset must be non-negative
    )
    raise_on_exhausted: bool = Field(
        default=False,
        description="whether to raise an exception when pagination is exhausted.",
    )

    # Private attributes
    _page: int = PrivateAttr(default=0)

    def run(self) -> int:
        if self.max_pages is not None and self._page >= self.max_pages:
            _msg = f"paginate exhausted after {self._page} pages"
            if self.raise_on_exhausted:
                raise RuntimeError(_msg)
            else:
                self.warning(_msg)
                return self.offset

        _current = self.offset
        self.offset += self.page_size
        self._page += 1
        self.debug(f"paginate to page {self._page} OK.")
        return _current

    def next(self) -> int:
        return self.run()

    def reset(self) -> None:
        self.offset = 0
        self._page = 0
        self.debug("reset OK.")
