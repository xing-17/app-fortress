from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any


class LocalObjectClient:
    """
    Local filesystem object management.

    Methods:
        write_bytes(path: Path, data: bytes) -> None:
            Write raw bytes to path, creating parent directories as needed.
        read_bytes(path: Path) -> bytes:
            Read raw bytes from path.
        list_objects(path, since=None, until=None, limit=None) -> list[dict[str, Any]]:
            List files under path (directories are excluded), optionally filtered by modified time and limit.
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
    def list_objects(
        path: Path,
        since: datetime | float | None = None,
        until: datetime | float | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        _om_list: list[dict[str, Any]] = []
        if not path.is_dir():
            return []
        if since is not None and isinstance(since, datetime):
            since = since.timestamp()
        if until is not None and isinstance(until, datetime):
            until = until.timestamp()
        for _path in path.rglob("*"):
            if _path.is_file():
                _meta: dict[str, Any] = LocalObjectClient.get_object(_path)
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
        if limit and limit <= len(_om_list):
            _om_list = _om_list[:limit]
        return _om_list

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
