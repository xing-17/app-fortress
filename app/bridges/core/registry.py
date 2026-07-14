from __future__ import annotations

from app.bridges.resources._registry.registry import BaseRegistry


class BridgesCoreClusterRegistry(BaseRegistry):
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
        super().__init__(
            name="core",
            path=path,
        )
        self._set_log_prefix(f"BridgesCoreClusterRegistry({self.file_name})")
        self.load()
