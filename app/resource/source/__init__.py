from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from ._common import BaseDataset, BaseSource, SourceFactory

if TYPE_CHECKING:
    from .tushare import TushareDataset, TushareSource

# Provider classes are resolved on first access so each provider loads independently.
_LAZY: dict[str, str] = {
    "TushareSource": ".tushare",
    "TushareDataset": ".tushare",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        return getattr(import_module(_LAZY[name], __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseSource",
    "BaseDataset",
    "SourceFactory",
    "TushareSource",
    "TushareDataset",
]
