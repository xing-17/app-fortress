from __future__ import annotations

import json
import threading
from collections import deque
from time import monotonic

import psutil

from app.bridges.machine._service.snapshot import MachineSnapshot
from app.bridges.resources.base.servicehealth import ServiceHealth
from app.bridges.resources.base.servicelike import ServiceLike
from app.common.core.setting import GlobalSetting
from app.common.plugin import (
    LogPlugin,
    StopwatchPlugin,
    TimePlugin,
)
from app.common.setting.bridges import BridgesMachineSetting
from app.common.setting.system import SystemSetting


class MachineService(
    LogPlugin,
    TimePlugin,
    StopwatchPlugin,
    ServiceLike,
):
    """
    系统指标采集服务（后台线程定时采样，缓冲区保存历史数据）。

    提供定时采集系统资源指标（CPU、内存、磁盘、网络、进程等）的后台服务，
    采样数据存储在固定大小的循环缓冲区中，支持实时查询和历史回溯。

    采样内容:
        - CPU: 使用率百分比
        - 内存: 使用率、已用/总量（MB）
        - 交换分区: 使用率百分比
        - 磁盘: 使用率、已用/总量（MB）
        - 进程: 当前进程的内存/CPU 使用、线程数
        - 网络: 发送/接收流量（MB，累计值）

    Attributes:
        setting (BridgesMachineSetting): Machine 服务配置。
        module_name (str): 模块名称，固定为 "machine"。
        _interval_seconds (int): 采样间隔（秒），从配置中读取。
        _max_samples (int): 缓冲区最大样本数，从配置中读取。
        _buffer (deque[dict]): 固定大小的循环缓冲区，保存采样历史。
        _lock (threading.Lock): 保护缓冲区的线程锁。
        _stop (threading.Event): 停止信号事件。
        _worker (threading.Thread): 后台采样线程（daemon）。
        _last_active_time (float | None): 最后活跃时间戳（monotonic）。

    Public Methods:
        start() -> None:
            启动后台采样线程（幂等，重复调用安全）。

        stop() -> None:
            停止后台采样线程，等待最多 5 秒。

        current() -> dict:
            立即采样并返回当前系统指标（不依赖缓冲区）。

        sample() -> MachineSnapshot:
            立即采样并返回 MachineSnapshot 对象。

        check() -> dict:
            返回系统基本信息（name, version, env, timezone）。

        health() -> ServiceHealth:
            返回服务健康状态（工作线程状态、最后活跃时间等）。

        history(minutes: int = None) -> list[dict]:
            返回历史采样数据。
            - minutes=None: 返回缓冲区中所有样本。
            - minutes=N: 返回最近 N 分钟的样本（根据采样间隔估算）。

        export() -> dict[str, Any]:
            导出服务配置和运行时状态。

        describe() -> str:
            返回服务状态的 JSON 字符串表示。

    Private Methods:
        _loop() -> None:
            后台采样循环，每隔 interval_seconds 采样一次并写入缓冲区。

        _sample() -> MachineSnapshot:
            执行一次系统指标采样，返回 MachineSnapshot 对象。

        _update_last_active_time() -> None:
            更新最后活跃时间戳。

    Example:
        >>> service = MachineService()
        >>> service.start()  # 启动后台采样
        >>> current_data = service.current()  # 获取当前指标
        >>> print(f"CPU: {current_data['cpu_percent']}%")
        >>> history_data = service.history(minutes=5)  # 获取最近 5 分钟
        >>> service.stop()  # 停止服务
    """

    def __init__(self) -> None:
        self.setting: BridgesMachineSetting = GlobalSetting.bridges.machine
        self._last_active_time: float | None = None
        self._interval_seconds: int = self.setting.interval_seconds
        self._max_samples: int = self.setting.max_samples
        self._buffer: deque[dict] = deque(maxlen=self._max_samples)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._worker_name: str = "machine-service-worker"
        self._worker = threading.Thread(
            target=self._loop,
            daemon=True,
            name=self._worker_name,
        )
        self._set_log_prefix("MachineService()")

    @property
    def module_name(self) -> str:
        return "machine"

    def start(self) -> None:
        if not self._worker.is_alive():
            self._worker.start()
        self.info("start: OK.")

    def stop(self) -> None:
        if self._worker.is_alive():
            self._stop.set()
            self._worker.join(timeout=5)
        self.info("stop: OK.")

    # ──INTERNAL──────────────────────────────────

    def _update_last_active_time(self) -> None:
        self._last_active_time: float = monotonic()

    def _loop(self) -> None:
        psutil.cpu_percent()
        # 等待 interval 秒，或收到停止信号
        while not self._stop.wait(self._interval_seconds):
            self._update_last_active_time()
            sample: MachineSnapshot = self._sample()
            with self._lock:
                _sample_export: dict = sample.export()
                self._buffer.append(_sample_export)

    def _sample(self) -> MachineSnapshot:
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        disk = psutil.disk_usage("/")

        # CPU 数据
        cpu_percent = psutil.cpu_percent()

        # Memory 数据
        mem_percent = vm.percent
        mem_used_mb = round(vm.used / 1024**2)
        mem_total_mb = round(vm.total / 1024**2)

        # Disk 数据
        swap_percent = sw.percent
        disk_percent = disk.percent
        disk_used_mb = round(disk.used / 1024**2)
        disk_total_mb = round(disk.total / 1024**2)

        # Process 数据（OOM 排查关键指标）
        try:
            proc = psutil.Process()
            with proc.oneshot():
                proc_mem_mb = round(proc.memory_info().rss / 1024**2)
                proc_mem_percent = round(proc.memory_percent(), 2)
                proc_cpu_percent = round(proc.cpu_percent(interval=None), 2)
                proc_workers = proc.num_threads()
        except Exception as e:
            self.warning(f"_sample: process fail {e}")
            proc_mem_mb = None
            proc_mem_percent = None
            proc_cpu_percent = None
            proc_workers = None

        # Network 数据（累计值，前端做差得速率）
        try:
            net = psutil.net_io_counters()
            net_sent_mb = round(net.bytes_sent / 1024**2)
            net_recv_mb = round(net.bytes_recv / 1024**2)
        except Exception as e:
            self.warning(f"_sample: network fail {e}")
            net_sent_mb = None
            net_recv_mb = None

        snapshot = MachineSnapshot(
            cpu_percent=cpu_percent,
            mem_percent=mem_percent,
            mem_used_mb=mem_used_mb,
            mem_total_mb=mem_total_mb,
            swap_percent=swap_percent,
            disk_percent=disk_percent,
            disk_used_mb=disk_used_mb,
            disk_total_mb=disk_total_mb,
            proc_mem_mb=proc_mem_mb,
            proc_mem_percent=proc_mem_percent,
            proc_cpu_percent=proc_cpu_percent,
            proc_workers=proc_workers,
            net_sent_mb=net_sent_mb,
            net_recv_mb=net_recv_mb,
        )
        return snapshot

    # ──EXTERNAL──────────────────────────────────

    def current(self) -> dict:
        sample = self._sample()
        return sample.export()

    def sample(self) -> MachineSnapshot:
        return self._sample()

    def check(self) -> dict:
        sys_setting: SystemSetting = GlobalSetting.system
        return {
            "status": "ok",
            "name": sys_setting.name,
            "version": sys_setting.version,
            "env": sys_setting.env,
            "timezone": sys_setting.timezone,
        }

    def health(self):
        is_alive: bool = self._worker.is_alive()
        last_active_time: float | None = self._last_active_time

        return ServiceHealth(
            service=self.module_name,
            worker_name=self._worker.name,
            worker_alive=is_alive,
            worker_daemon=self._worker.daemon,
            worker_ident=self._worker.ident,
            worker_count=threading.active_count(),
            last_active_time=last_active_time,
        )

    def history(
        self,
        minutes: int = None,
    ) -> list[dict]:
        if minutes is None:
            with self._lock:
                samples: list[dict] = list(self._buffer)
        else:
            n = max(1, int(minutes * 60 / self._interval_seconds))
            with self._lock:
                samples = list(self._buffer)
            samples = samples[-n:]

        samples.sort(key=lambda x: x["timestamp"], reverse=False)
        return samples

    def export(self) -> dict:
        return {
            "setting": self.setting.export(),
            "module": self.module_name,
            "extra": {
                "last_active_time": self._last_active_time,
                "current_buffer_size": len(self._buffer),
            },
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
