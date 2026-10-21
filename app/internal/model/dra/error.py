from __future__ import annotations


class DRAError(Exception):
    """Base class of all DRA errors."""


class DRARejectedError(DRAError):
    """The statement or mount was refused before reaching the engine."""


class DRAQueryTimeoutError(DRAError):
    """The query was interrupted by the timeout."""


class DRAQueryError(DRAError):
    """The engine failed the query (syntax, permission, out of memory, ...)."""
