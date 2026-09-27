from __future__ import annotations

import os
from datetime import datetime
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Iterator

from app.internal.util.clock import IClock


class LocalObjectClient:
    """
    Local filesystem object management.

    Methods:
        write_bytes(path: Path, data: bytes) -> None:
            Write raw bytes to path, creating parent directories as needed.
        read_bytes(path: Path) -> bytes:
            Read raw bytes from path.
        list_objects(path, pattern=None, since=None, until=None, recursive=True) -> list[dict[str, Any]]:
            List files under path (directories are excluded), optionally filtered by pattern/modified time.
            When recursive is False, only direct children of path are listed.
        list_folders(path, pattern=None, recursive=True) -> list[dict[str, Any]]:
            List subdirectories under path. When recursive is False, only direct children of path are listed.
        get_object(path: Path) -> dict[str, Any]:
            Return path and stat metadata for a single filesystem entry.

    """

    @staticmethod
    def write_bytes(
        path: Path,
        data: bytes,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_bytes(data)

    @staticmethod
    def read_bytes(path: Path) -> bytes:
        return path.read_bytes()

    @staticmethod
    def _get_glob_iter(
        path: Path,
        recursive: bool = True,
    ) -> Iterator[Path]:
        if recursive:
            return path.rglob("*")
        else:
            return path.glob("*")

    @staticmethod
    def list_objects(
        path: Path,
        pattern: str | None = None,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        _om_list: list[dict[str, Any]] = []
        if not path.is_dir():
            return []
        if since is not None and isinstance(since, datetime):
            _dt: datetime = IClock.from_datetime(since, timezone="UTC")
            since = _dt.timestamp()
        if until is not None and isinstance(until, datetime):
            _dt: datetime = IClock.from_datetime(until, timezone="UTC")
            until = _dt.timestamp()
        _iter = LocalObjectClient._get_glob_iter(
            path=path,
            recursive=recursive,
        )
        for _path in _iter:
            if _path.is_file():
                _res: Path = _path.resolve()
                if pattern and not fnmatchcase(str(_res), pattern):
                    continue
                _meta: dict[str, Any] = LocalObjectClient.get_object(_res)
                _m_stat: dict[str, Any] = _meta.get("stat", {})
                _st_mtime: float | None = _m_stat.get("st_mtime", None)
                if since is not None and _st_mtime is not None and _st_mtime < since:
                    continue
                if until is not None and _st_mtime is not None and _st_mtime > until:
                    continue
                _om_list.append(_meta)
        _om_list: list[dict[str, Any]] = sorted(
            _om_list,
            key=lambda x: x["path"],
        )
        return _om_list

    @staticmethod
    def list_folders(
        path: Path,
        pattern: str | None = None,
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        _folders: list[dict[str, Any]] = []
        if not path.is_dir():
            return []
        _iter = LocalObjectClient._get_glob_iter(
            path=path,
            recursive=recursive,
        )
        for _path in _iter:
            if _path.is_dir():
                _res: Path = _path.resolve()
                if pattern and not fnmatchcase(str(_res), pattern):
                    continue
                _meta: dict[str, Any] = LocalObjectClient.get_object(_res)
                _folders.append(_meta)
        _folders = sorted(
            _folders,
            key=lambda x: x["path"],
        )
        return _folders

    @staticmethod
    def get_object(path: Path) -> dict[str, Any]:
        _stat: os.stat_result = path.stat()
        return {
            "path": path,
            "stat": {
                "st_mode": _stat.st_mode,
                "st_ino": _stat.st_ino,
                "st_dev": _stat.st_dev,
                "st_nlink": _stat.st_nlink,
                "st_uid": _stat.st_uid,
                "st_gid": _stat.st_gid,
                "st_size": _stat.st_size,
                "st_atime": _stat.st_atime,
                "st_mtime": _stat.st_mtime,
                "st_ctime": _stat.st_ctime,
            },
        }
