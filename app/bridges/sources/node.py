from __future__ import annotations

import threading
import traceback
from typing import Any

import polars as pl

from app.bridges.resources.destinations.base.destination import BaseDestination
from app.bridges.resources.providers.base.provider import BaseProvider
from app.bridges.resources.sources.base.source import BaseSource
from app.bridges.sources.context import SourceContext
from app.bridges.sources.quality import SourceQuality
from app.bridges.sources.state import SourceState
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)


class SourceNode(
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
):
    """
    Source 层最小执行节点。

    负责执行单次原子数据抓取任务，包含完整的数据获取、转换、质量检查和写入流程。
    基于 SourceContext 配置，调用 Provider 和 Source 获取数据，写入 Destinations。

    执行流程：
        1. start() - 标记开始，设置状态为 RUNNING
        2. invoke() - 调用 source.run() 获取原始数据
        3. invoke() - 调用 source.transform() 转换数据
        4. write() - 写入所有 destinations
        5. write() - 生成数据质量报告（如果启用）
        6. finish() - 标记完成，设置状态为 SUCCESS

    取消机制：
        - 支持通过 cancel() 方法取消执行
        - 使用 threading.Event 实现取消信号
        - 在 run() 开始时检查取消状态

    Attributes:
        context (SourceContext): 执行上下文，包含所有配置信息
        id (str): 节点唯一标识（来自 context.id）
        provider (BaseProvider): 数据提供商实例
        source (BaseSource): 数据源实例，定义获取方法和转换规则
        destinations (list[BaseDestination]): 写出目标列表
        params (dict[str, Any]): 运行参数，如 {"start_date": "2024-01-01"}
        state (SourceState): 执行状态追踪对象
        quality (SourceQuality): 数据质量报告对象

    Methods:
        run() -> SourceState:
            执行完整的数据抓取流程，返回执行状态。
            处理异常并自动清理资源。

        invoke() -> pl.DataFrame:
            调用数据源获取并转换数据。
            先调用 source.run() 获取原始数据，再调用 source.transform() 转换。

        write(data: pl.DataFrame) -> None:
            将数据写入所有目标存储。
            如果启用质量检查，生成并写入质量报告。

        cancel() -> None:
            取消当前节点的执行。
            设置取消信号，run() 方法会在开始时检查并跳过执行。

    Example:
        >>> # 基本使用
        >>> context = SourceContext(
        ...     request_id="req_123",
        ...     pipeline_id="pipe_456",
        ...     provider=tushare_provider,
        ...     source=daily_basic_source,
        ...     destinations=[postgres_dest],
        ...     params={"start_date": "2024-01-01"},
        ... )
        >>> node = SourceNode(context)
        >>> state = node.run()
        >>> print(f"Status: {state.status}, Rows: {state.rows}")
        
        >>> # 取消执行
        >>> node = SourceNode(context)
        >>> node.cancel()
        >>> state = node.run()
        >>> print(state.status)  # CANCELED

    """

    def __init__(
        self,
        context: SourceContext,
    ):
        self.context: SourceContext = context
        self.id: str = context.id
        self.provider: BaseProvider = context.provider
        self.source: BaseSource = context.source
        self.destinations: list[BaseDestination] = context.destinations
        self.params: dict[str, Any] = context.params
        self.state = SourceState()
        self.quality: SourceQuality = SourceQuality(
            source_name=self.source.name,
            source_context_id=self.context.id,
        )
        self._cancel_event = threading.Event()
        self._set_log_prefix(f"SourceNode({self.id})")

    def run(self) -> SourceState:
        self.tick("run")
        self.state.start()
        self.info(f"run: source {self.source.name} started.")
        data: pl.DataFrame | None = None

        if self._is_cancelled():
            self.state.cancel()
            self.info(f"run: source {self.source.name} cancelled.")
            return self.state

        try:
            data = self.invoke()
            rows = data.height
            if not data.is_empty():
                self.write(data)
            self.state.finish(rows=rows)
        except Exception as e:
            self.error(f"run: source {self.source.name} failed: {e}")
            self.error(f"run: traceback:\n{traceback.format_exc()}")
            self.state.fail(error=str(e))
        finally:
            if data is not None:
                del data
        status = self.state.status.value
        duration = self.tock("run")
        self.info(f"run: source {self.source.name} finished {status}.")
        self.info(f"run: duration {duration:.2f}s.")
        return self.state

    def invoke(self) -> pl.DataFrame:
        self.tick("invoke")
        result = self.source.run(
            provider=self.provider,
            params=self.params,
        )
        result = self.source.transform(result)
        duration = self.tock("invoke")
        self.info(f"invoke: source {self.source.name} returned {result.height} rows OK.")
        self.debug(f"invoke: duration {duration:.2f}s.")
        return result

    def cancel(self) -> None:
        self._cancel_event.set()

    def _is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def write(
        self,
        data: pl.DataFrame,
    ) -> None:
        self.tick("write")

        # Generate quality report if enabled
        is_quality_enabled = self.source.setting.quality_enabled
        if is_quality_enabled:
            current_datetime = self._get_current_datetime()
            self.quality = SourceQuality(
                source_name=self.source.name,
                source_context_id=self.context.id,
                data=data,
                primary_keys=self.source.setting.primary_fields,
                extra={
                    "status": self.state.status.value,
                    "started_at": self.state.start_at_repr,
                    "reported_at": current_datetime.isoformat(),
                    "error": self.state.error,
                },
            )
            for destination in self.destinations:
                self._write_source_quality_to_destination(
                    quality=self.quality,
                    destination=destination,
                )

        # Write data to all destinations
        n_dests = len(self.destinations)
        for destination in self.destinations:
            self._write_source_to_destination(
                data=data,
                destination=destination,
            )

        duration = self.tock("write")
        self.debug(f"write: {data.height} rows to {n_dests} destinations OK.")
        self.debug(f"write: duration {duration:.2f}s.")

    def _write_source_to_destination(
        self,
        data: pl.DataFrame,
        destination: BaseDestination,
    ) -> None:
        destination.write_source(
            df=data,
            table_name=self.source.name,
            partition_col=self.source.setting.partition.column,
            partition_prefix=self.source.setting.partition.prefix,
        )

    def _write_source_quality_to_destination(
        self,
        quality: SourceQuality,
        destination: BaseDestination,
    ) -> None:
        destination.write_source_quality(
            quality=quality,
        )
