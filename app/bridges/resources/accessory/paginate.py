from __future__ import annotations

from typing import Any, Literal

from app.bridges.resources.accessory.base import BaseAccessory


class Paginate(BaseAccessory):
    """
    分页控制器

    管理数据抓取或数据库查询的分页状态。

    Attributes:
        page_size: 每页拉取的数据条数（步长），默认 2000。
        max_pages: 最多拉取的页数，默认 10。
        offset: 当前的读取偏移量。
        _count: 已翻页的次数计数器。

    Examples:
        >>> p = Paginate(page_size=1000, max_pages=5)
        >>> p.offset  # 0
        >>> p.next()  # 1000
        >>> p.offset  # 1000
        >>> p.next()  # 2000
        >>> p.offset  # 2000
        >>> p.reset()
        >>> p.offset  # 0

    """

    _default_page_size: int = 2000
    _default_max_pages: int = 10
    _default_offset: int = 0

    def __init__(
        self,
        page_size: int | None = None,
        max_pages: int | None = None,
        offset: int | None = None,
    ) -> None:
        super().__init__()
        self.page_size: int = self._resolve_int(
            value=page_size,
            default=self._default_page_size,
            name="page_size",
        )
        self.max_pages: int = self._resolve_int(
            value=max_pages,
            default=self._default_max_pages,
            name="max_pages",
        )
        self.offset: int = self._resolve_int(
            value=offset,
            default=self._default_offset,
            name="offset",
        )
        self._count: int = 0
        self._set_log_prefix(f"Paginate({self.uuid})")

    def _resolve_int(
        self,
        value: int | None,
        default: int,
        name: str,
    ) -> int:
        if value is None:
            return default
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be integer, got {value}")
        return value

    def reset(self) -> None:
        self.offset = self._default_offset
        self._count = 0
        self.debug(f"reset: offset at {self.offset} OK.")

    def next(self) -> tuple[int, int]:
        current = self.offset
        self.offset += self.page_size
        self.debug(f"next: offset at {self.offset} OK.")
        return (current, self.page_size)

    def __enter__(self) -> Paginate:
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> Literal[False]:
        return False

    def export(self) -> dict[str, Any]:
        result = super().export()
        result["page_size"] = self.page_size
        result["max_pages"] = self.max_pages
        result["offset"] = self.offset
        return result
