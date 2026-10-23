from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

import psutil

from app.internal.constant.servicekind import ServiceKind
from app.service._common._service import BaseService
from app.service.machine.service.snapshot import MachineSnapshot
from app.setting.service import MachineServiceSetting

_MB = 1024**2

# CPU percent is measured since the previous call
# give the first reading a window
_WARMUP_SECONDS = 1.0


class MachineService(BaseService[MachineServiceSetting]):
    """
    Records the state of the host machine, one snapshot every `interval_seconds`

    A worker thread samples cpu, memory, swap, disk, network and this process, and keeps the
    last `max_snapshots` in memory (`retention_hours` of history, 12 hours by default). Nothing
    is persisted: a restart starts with an empty history. The first snapshot is taken shortly
    after start, so `list_snapshots` is empty until then.

    Args:
    ----------
        setting (MachineServiceSetting):
            Machine service setting

    Methods:
    ----------
        list_snapshots(hours=None) -> list[dict]:
            Snapshots oldest first, all of them or those of the last `hours`
        sample() -> MachineSnapshot:
            Read the machine now, not recorded
        health() -> dict:
            Kind and state plus the number of snapshots held

    """

    kind = ServiceKind.MACHINE

    def __init__(
        self,
        setting: MachineServiceSetting,
    ) -> None:
        super().__init__(setting)
        self._snapshots: deque[MachineSnapshot] = deque(maxlen=setting.max_snapshots)
        self._snapshots_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        # One Process object for good, its cpu_percent is measured between two calls
        self._process: psutil.Process | None = None

    def _start(self) -> None:
        self._process = psutil.Process()
        # Prime the counters so the first reading measures a window and not zero
        psutil.cpu_percent(interval=None)
        self._process.cpu_percent(interval=None)

        self._stop_event = threading.Event()
        self._worker = threading.Thread(
            target=self._loop,
            args=(self._stop_event,),
            name="machine-service-worker",
            daemon=True,
        )
        self._worker.start()

    def _stop(self) -> None:
        self._stop_event.set()
        if self._worker is not None:
            self._worker.join(timeout=5)
            self._worker = None

    def health(self) -> dict:
        _res: dict = super().health()
        with self._snapshots_lock:
            _res["snapshots"] = len(self._snapshots)
        return _res

    # --------------------------------------------------
    # Sampling
    # --------------------------------------------------

    def _loop(
        self,
        stop: threading.Event,
    ) -> None:
        _delay: float = min(_WARMUP_SECONDS, self.setting.interval_seconds)
        while not stop.wait(_delay):
            self._record()
            _delay = self.setting.interval_seconds

    def _record(self) -> None:
        # A failed reading is skipped, it must not end the worker
        try:
            _snapshot: MachineSnapshot = self.sample()
        except Exception as e:
            self.log.warning(
                "machine sample failed",
                metadata={"error": type(e).__name__},
            )
            return
        with self._snapshots_lock:
            self._snapshots.append(_snapshot)

    def sample(self) -> MachineSnapshot:
        _memory = psutil.virtual_memory()
        _swap = psutil.swap_memory()
        _disk = psutil.disk_usage("/")

        # Process figures are what an OOM investigation needs, the machine may still be readable without
        _proc: dict[str, Any] = {}
        try:
            _process: psutil.Process = self._process or psutil.Process()
            with _process.oneshot():
                _proc["proc_mem_mb"] = round(_process.memory_info().rss / _MB)
                _proc["proc_mem_percent"] = round(_process.memory_percent(), 2)
                _proc["proc_cpu_percent"] = round(_process.cpu_percent(interval=None), 2)
                _proc["proc_workers"] = _process.num_threads()
        except Exception as e:
            self.log.warning("machine process read failed", metadata={"error": type(e).__name__})
            _proc = {}

        _net: dict[str, Any] = {}
        try:
            _counters = psutil.net_io_counters()
            _net["net_sent_mb"] = round(_counters.bytes_sent / _MB)
            _net["net_recv_mb"] = round(_counters.bytes_recv / _MB)
        except Exception as e:
            self.log.warning("machine network read failed", metadata={"error": type(e).__name__})

        return MachineSnapshot(
            timestamp=time.time(),
            cpu_percent=psutil.cpu_percent(interval=None),
            mem_percent=_memory.percent,
            mem_used_mb=round(_memory.used / _MB),
            mem_total_mb=round(_memory.total / _MB),
            swap_percent=_swap.percent,
            disk_percent=_disk.percent,
            disk_used_mb=round(_disk.used / _MB),
            disk_total_mb=round(_disk.total / _MB),
            **_proc,
            **_net,
        )

    # --------------------------------------------------
    # History
    # --------------------------------------------------

    def list_snapshots(
        self,
        hours: float | None = None,
    ) -> list[dict[str, Any]]:
        with self._snapshots_lock:
            _items: list[MachineSnapshot] = list(self._snapshots)

        if hours is not None:
            _since: float = time.time() - hours * 3600
            _items = [s for s in _items if s.timestamp >= _since]
        return [s.export() for s in _items]
