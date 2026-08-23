from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from bastion.control.asset.base.base import IAssetAdaptorLike


@runtime_checkable
class ILocalAdaptorLike(IAssetAdaptorLike, Protocol):
    """
    Protocol an adaptor that can read files from local filesystem.

    Methods:
        list_objects: List files in a directory matching a pattern, with optional time slicing and limit

    """

    def list_objects(
        self,
        path: Path,
        pattern: str,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[Path]: ...


class LocalAdaptor(ILocalAdaptorLike):
    """
    An adaptor that can read files from local filesystem.

    Methods:
        list_objects: List files in a directory matching a pattern, with optional time slicing and limit

    """

    def __init__(self) -> None:
        pass

    def _slice_by_time(
        self,
        files: list[Path],
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Path]:
        if since is None and until is None:
            return files
        _filtered: list[Path] = []
        for file in files:
            _stat = file.stat()
            _modified_at: datetime = datetime.fromtimestamp(
                timestamp=_stat.st_mtime,
                tz=UTC,
            )
            if since and _modified_at < since:
                continue
            if until and _modified_at > until:
                continue
            _filtered.append(file)
        return _filtered

    def _slice_by_limit(
        self,
        files: list[Path],
        limit: int | None = None,
    ) -> list[Path]:
        if limit is None:
            return files
        if limit <= 0 or limit > len(files):
            return files
        return files[:limit]

    def list_objects(
        self,
        path: Path,
        pattern: str,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[Path]:
        _result: list[Path] = []
        for file in path.rglob(pattern):
            _result.append(file)
        _result = self._slice_by_time(_result, since=since, until=until)
        _result = self._slice_by_limit(_result, limit=limit)
        _result.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return _result
