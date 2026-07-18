from __future__ import annotations

import json
import os
import tempfile
import threading
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from app.common.plugin import (
    LogPlugin,
    TimePlugin,
)


class BaseRegistry(
    LogPlugin,
    TimePlugin,
):
    """
    集群执行历史的本地 JSON 持久化注册表。每次修改立即写入磁盘。

    ### Params:
        name: 注册表名称，用于日志标识。
        path: 注册表 JSON 文件路径。
        max_items: 最大记录数，超过时删除最旧的记录。默认 1000。

    ### Attributes:
        name (str): 注册表名称。
        _path (Path): 注册表文件路径。
        _lock (threading.Lock): 线程锁，确保并发访问安全。
        _items (OrderedDict): 内存中的注册表数据，键为 request_id，值为对应的执行状态字典。
        _file_name (str): 注册表文件名。
        _max_items (int): 注册表最大记录数，超过该数量时会删除最旧的记录。

    ### Example:

        >>> registry = BaseRegistry("my_registry", ".cache/registry.json")
        >>> registry.load()
        >>> registry.upsert("req_123", {"status": "DONE"})  # 立即写入磁盘

    """

    def __init__(
        self,
        name: str,
        path: str,
        max_items: int = 1000,
    ) -> None:
        super().__init__()
        self.name = name
        self._path = Path(path)
        self._lock = threading.Lock()
        self._items: OrderedDict[str, dict[str, Any]] = self._init_items()
        self._file_name = self._path.name
        self._max_items = max_items
        self._set_log_prefix(f"BaseRegistry({self._file_name})")

    def _init_items(self) -> OrderedDict[str, dict[str, Any]]:
        result: OrderedDict[str, dict[str, Any]] = OrderedDict()
        return result

    def load(self) -> None:
        # New JSON file
        if not self._path.exists():
            with self._lock:
                self._items: OrderedDict[str, dict] = self._init_items()
                self._flush()
            self.debug("load: new registry create OK.")
            return

        # Load OK from JSON file
        try:
            with self._lock:
                with open(
                    file=self._path,
                    mode="r",
                    encoding="utf-8",
                ) as f:
                    self._items: OrderedDict[str, dict] = OrderedDict(json.load(f))
            self.debug(f"load: {len(self._items)} items OK.")

        # loading fails, init empty data
        except Exception as e:
            with self._lock:
                self._items = self._init_items()
                self._flush()
            self.warning(f"load: fail {e}")
            self.debug("load: new registry create OK.")

    def save(self) -> None:
        with self._lock:
            self._flush()
        self.debug("save: OK.")

    def _flush(self) -> None:
        # Ensure the max items limit
        while len(self._items) > self._max_items:
            self._items.popitem(last=False)

        # Ensure the parent directory exists
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Atomic write items to JSON file
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self._path.parent,
            suffix=".tmp",
        )
        try:
            with os.fdopen(
                fd=temp_fd,
                mode="w",
                encoding="utf-8",
            ) as f:
                json.dump(
                    self._items,
                    f,
                    indent=4,
                    ensure_ascii=False,
                    default=str,
                )
            os.replace(temp_path, self._path)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def reset(self) -> None:
        with self._lock:
            _len_items = len(self._items)
            self._items = self._init_items()
            self._flush()
        self.info(f"reset: {_len_items} items OK.")

    def upsert(
        self,
        index: str,
        data: dict,
    ) -> None:
        _data = deepcopy(data)
        _current: datetime = self._get_current_datetime()
        _data["__upserted_at__"] = _current.isoformat()
        with self._lock:
            self._items.pop(index, None)
            self._items[index] = _data
            self._flush()

    def remove(
        self,
        index: str,
    ) -> None:
        with self._lock:
            if index in self._items:
                self._items.pop(index, None)
                self._flush()

    def get(
        self,
        index: str,
    ) -> dict | None:
        with self._lock:
            item = self._items.get(index)
            if item:
                return deepcopy(item)
            else:
                return None

    def all(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(dict(self._items))

    def export(self) -> dict:
        return {
            "path": str(self._path),
            "file": self._file_name,
            "count": len(self._items),
            "max": self._max_items,
            "items": dict(self._items),
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
