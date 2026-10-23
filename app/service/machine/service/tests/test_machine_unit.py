from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import psutil
import pytest

from app.internal.constant.servicekind import ServiceKind
from app.internal.constant.servicestate import ServiceState
from app.internal.logstream import LogStream
from app.resource._global.logstreams import GlobalLogStreams
from app.service.machine.service import service as machine_module
from app.service.machine.service.service import MachineService
from app.service.machine.service.snapshot import MachineSnapshot
from app.setting.service import MachineServiceSetting


@pytest.fixture
def log(monkeypatch):
    _log = MagicMock(spec=LogStream)
    monkeypatch.setattr(GlobalLogStreams, "resolve", lambda value, default: _log)
    return _log


@pytest.fixture
def service(log):
    _service = MachineService(MachineServiceSetting())
    yield _service
    _service.stop()


def _snapshot(timestamp: float) -> MachineSnapshot:
    return MachineSnapshot(
        timestamp=timestamp,
        cpu_percent=1.0,
        mem_percent=2.0,
        mem_used_mb=3,
        mem_total_mb=4,
        swap_percent=0.0,
        disk_percent=5.0,
        disk_used_mb=6,
        disk_total_mb=7,
    )


def _wait_for(predicate, seconds: float = 5.0) -> bool:
    _deadline = time.monotonic() + seconds
    while time.monotonic() < _deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class TestSample:
    def test_kind(self, service):
        assert service.kind == ServiceKind.MACHINE

    def test_reads_the_machine(self, service):
        _snap = service.sample()
        assert 0 <= _snap.cpu_percent <= 100
        assert 0 <= _snap.mem_percent <= 100
        assert _snap.mem_total_mb > 0
        assert _snap.disk_total_mb > 0
        assert _snap.timestamp == pytest.approx(time.time(), abs=5)

    def test_reads_this_process(self, service):
        _snap = service.sample()
        assert _snap.proc_mem_mb > 0
        assert _snap.proc_workers >= 1

    def test_reads_the_network_totals(self, service):
        _snap = service.sample()
        assert _snap.net_sent_mb >= 0
        assert _snap.net_recv_mb >= 0

    def test_sample_is_not_recorded(self, service):
        service.sample()
        assert service.list_snapshots() == []

    def test_unreadable_process_leaves_its_fields_empty(self, service, log, monkeypatch):
        def _fail(*args, **kwargs):
            raise psutil.AccessDenied()

        monkeypatch.setattr(machine_module.psutil, "Process", _fail)
        _snap = service.sample()
        assert _snap.proc_mem_mb is None
        assert _snap.proc_mem_percent is None
        assert _snap.proc_cpu_percent is None
        assert _snap.proc_workers is None
        assert _snap.mem_total_mb > 0
        log.warning.assert_called_once()

    def test_unreadable_network_leaves_its_fields_empty(self, service, log, monkeypatch):
        def _fail():
            raise OSError("no network")

        monkeypatch.setattr(machine_module.psutil, "net_io_counters", _fail)
        _snap = service.sample()
        assert _snap.net_sent_mb is None
        assert _snap.net_recv_mb is None
        assert _snap.proc_mem_mb is not None
        log.warning.assert_called_once()


class TestRecord:
    def test_record_keeps_the_snapshot(self, service):
        service._record()
        _res = service.list_snapshots()
        assert len(_res) == 1
        assert _res[0]["mem_total_mb"] > 0

    def test_failed_sample_is_skipped(self, service, log, monkeypatch):
        def _fail():
            raise OSError("boom")

        monkeypatch.setattr(machine_module.psutil, "virtual_memory", _fail)
        service._record()
        assert service.list_snapshots() == []
        log.warning.assert_called_once()

    def test_keeps_only_the_last_max_snapshots(self, log):
        # 0.05 hours at one per minute is 3 snapshots
        _service = MachineService(MachineServiceSetting(retention_hours=0.05))
        for _ in range(5):
            _service._record()
        assert len(_service.list_snapshots()) == 3


class TestListSnapshots:
    def test_empty_before_the_first_snapshot(self, service):
        assert service.list_snapshots() == []

    def test_oldest_first(self, service):
        _now = time.time()
        for _t in (_now - 120, _now - 60, _now):
            service._snapshots.append(_snapshot(_t))
        _stamps = [s["timestamp"] for s in service.list_snapshots()]
        assert _stamps == sorted(_stamps)

    def test_none_returns_all(self, service):
        _now = time.time()
        for _t in (_now - 86_400, _now - 3600, _now):
            service._snapshots.append(_snapshot(_t))
        assert len(service.list_snapshots()) == 3

    def test_hours_keeps_only_the_recent_ones(self, service):
        _now = time.time()
        for _t in (_now - 7200, _now - 1800, _now):
            service._snapshots.append(_snapshot(_t))
        assert len(service.list_snapshots(hours=1)) == 2
        assert len(service.list_snapshots(hours=0.1)) == 1
        assert len(service.list_snapshots(hours=3)) == 3

    def test_items_are_plain_dicts(self, service):
        service._snapshots.append(_snapshot(time.time()))
        _item = service.list_snapshots()[0]
        assert isinstance(_item, dict)
        assert {"timestamp", "cpu_percent", "mem_percent", "disk_percent", "net_sent_mb"} <= set(_item)


class TestLifecycle:
    def test_start_records_snapshots(self, service, monkeypatch):
        monkeypatch.setattr(machine_module, "_WARMUP_SECONDS", 0.01)
        service.start()
        assert service.state == ServiceState.RUNNING
        assert _wait_for(lambda: len(service.list_snapshots()) >= 1)

    def test_keeps_recording_every_interval(self, log, monkeypatch):
        monkeypatch.setattr(machine_module, "_WARMUP_SECONDS", 0.01)
        _service = MachineService(MachineServiceSetting(interval_seconds=1, retention_hours=2.0))
        _service.start()
        try:
            assert _wait_for(lambda: len(_service.list_snapshots()) >= 2)
        finally:
            _service.stop()

    def test_stop_ends_the_worker(self, service, monkeypatch):
        monkeypatch.setattr(machine_module, "_WARMUP_SECONDS", 0.01)
        service.start()
        _worker = service._worker
        assert _worker.is_alive()
        service.stop()
        assert not _worker.is_alive()
        assert service._worker is None
        assert service.state == ServiceState.STOPPED

    def test_stop_keeps_the_history(self, service):
        service._record()
        service.start()
        service.stop()
        assert len(service.list_snapshots()) == 1

    def test_can_start_again_after_stop(self, service, monkeypatch):
        monkeypatch.setattr(machine_module, "_WARMUP_SECONDS", 0.01)
        service.start()
        service.stop()
        service.start()
        assert _wait_for(lambda: len(service.list_snapshots()) >= 1)
        service.stop()

    def test_worker_survives_a_failed_sample(self, service, log, monkeypatch):
        monkeypatch.setattr(machine_module, "_WARMUP_SECONDS", 0.01)
        _calls = threading.Event()
        _real = machine_module.psutil.virtual_memory

        def _flaky():
            if not _calls.is_set():
                _calls.set()
                raise OSError("boom")
            return _real()

        monkeypatch.setattr(machine_module.psutil, "virtual_memory", _flaky)
        _service = MachineService(MachineServiceSetting(interval_seconds=1, retention_hours=2.0))
        _service.start()
        try:
            assert _wait_for(lambda: len(_service.list_snapshots()) >= 1)
        finally:
            _service.stop()


class TestHealth:
    def test_reports_the_snapshot_count(self, service):
        assert service.health()["snapshots"] == 0
        service._record()
        _res = service.health()
        assert _res["snapshots"] == 1
        assert _res["kind"] == "machine"
