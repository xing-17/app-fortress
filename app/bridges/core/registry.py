from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.common.plugin import LogPlugin, TimePlugin


class BridgesCoreClusterRegistry(
    LogPlugin,
    TimePlugin,
):
    """
    集群执行历史的本地 JSON 持久化注册表。

    Attributes:
        _path (Path): 注册表文件路径。
        _lock (threading.Lock): 线程锁，确保并发访问安全。
        _data (dict): 内存中的注册表数据，键为 request_id，值为对应的执行状态字典。
        file_name (str): 注册表文件名。

    Methods:
        load(): 从 JSON 文件加载注册表数据到内存。
        _flush(): 将内存中的注册表数据写入 JSON 文件。
        upsert(request_id, data): 插入或更新指定 request_id 的执行状态数据。
        get(request_id): 获取指定 request_id 的执行状态数据。
        all(): 获取所有注册表数据的副本。
        export(): 导出注册表的元信息，包括路径和记录数。

    Example:
        >>> registry = BridgesCoreClusterRegistry(".cache/bridges/registry.json")
        >>> registry.upsert(
        ...     "req_123",
        ...         {
        ...             "status": "DONE",
        ...             "started_at": "2024-06-05T12:00:00",
        ...             "finished_at": "2024-06-05T12:05:00",
        ...             ...
        ...         }
        ... )

    """

    def __init__(
        self,
        path: str,
    ) -> None:
        super().__init__()
        self._path = Path(path)
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        self.file_name = self._path.name
        self._set_log_prefix(f"BridgesCoreClusterRegistry({self.file_name})")
        self.load()

    def load(self) -> None:
        if not self._path.exists():
            self._data = {}
            self.info("load: no existing registry, created new.")
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            self.info(f"load: {len(self._data)} records restored.")
        except Exception as e:
            self._data = {}
            self.warning(f"load: failed ({e}), created new.")

    def clean(self) -> None:
        with self._lock:
            self._data = {}
            self.info("clean: registry cleared.")
            self._flush()

    def _flush(self) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(
                self._data,
                f,
                indent=4,
                ensure_ascii=False,
                default=str,
            )

    def upsert(
        self,
        request_id: str,
        data: dict,
    ) -> None:
        with self._lock:
            self._data[request_id] = data
            self._flush()

    def get(
        self,
        request_id: str,
    ) -> dict | None:
        return self._data.get(request_id)

    def all(self) -> dict[str, Any]:
        return dict(self._data)

    def export(self) -> dict:
        _data_export = {}
        for request_id, state in self._data.items():
            _data_export[request_id] = state

        return {
            "path": str(self._path),
            "count": len(self._data),
            "data": _data_export,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
