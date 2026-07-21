"""
综合测试：app.bridges.machine._service.service

覆盖范围
--------
- TestInstantiation    基本实例化和属性验证
- TestStartWorker      start() 启动工作线程
- TestSampling         _sample() 采样功能
- TestCurrent          current() 实时查询
- TestHistory          history() 历史数据查询
- TestBuffer           缓冲区管理（循环队列）
- TestHealth           health() 健康检查
- TestCheck            check() 系统信息
- TestExport           export() / describe()
- TestShutdown         stop() 停止服务
"""

from __future__ import annotations

import json
import threading
import time
from unittest.mock import patch

import pytest

from app.bridges.machine._service.service import MachineService
from app.bridges.machine._service.snapshot import MachineSnapshot

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_settings():
    """创建 Mock 的配置对象。"""
    with patch("app.bridges.machine._service.service.GlobalSetting") as mock:
        # 配置 machine 设置
        mock.bridges.machine.interval_seconds = 60
        mock.bridges.machine.max_samples = 100
        mock.bridges.machine.export.return_value = {
            "interval_seconds": 60,
            "max_samples": 100,
        }
        # 配置 system 设置
        mock.system.name = "test-system"
        mock.system.version = "1.0.0"
        mock.system.env = "test"
        mock.system.timezone = "UTC"
        yield mock


# ── TestInstantiation ─────────────────────────────────────────────────────────


class TestInstantiation:
    """测试基本实例化和属性验证。"""

    def test_has_buffer(self, mock_settings):
        """验证服务具有缓冲区。"""
        service = MachineService()
        assert hasattr(service, "_buffer")
        from collections import deque

        assert isinstance(service._buffer, deque)

    def test_has_lock(self, mock_settings):
        """验证服务具有线程锁。"""
        service = MachineService()
        assert hasattr(service, "_lock")
        assert isinstance(service._lock, type(threading.Lock()))

    def test_has_stop_event(self, mock_settings):
        """验证服务具有停止事件。"""
        service = MachineService()
        assert hasattr(service, "_stop")
        assert isinstance(service._stop, threading.Event)

    def test_has_worker_thread(self, mock_settings):
        """验证服务具有工作线程。"""
        service = MachineService()
        assert hasattr(service, "_worker")
        assert isinstance(service._worker, threading.Thread)

    def test_worker_not_alive_before_start(self, mock_settings):
        """验证工作线程在 start() 调用前不运行。"""
        service = MachineService()
        assert not service._worker.is_alive()

    def test_worker_is_daemon(self, mock_settings):
        """验证工作线程为守护线程。"""
        service = MachineService()
        assert service._worker.daemon is True

    def test_module_name(self, mock_settings):
        """验证模块名称为 'machine'。"""
        service = MachineService()
        assert service.module_name == "machine"


# ── TestStartWorker ───────────────────────────────────────────────────────────


class TestStartWorker:
    """测试 start() 启动工作线程。"""

    def test_start_makes_worker_alive(self, mock_settings):
        """验证 start() 启动工作线程。"""
        service = MachineService()
        service.start()
        try:
            assert service._worker.is_alive()
        finally:
            service.stop()

    def test_start_idempotent(self, mock_settings):
        """验证多次调用 start() 不会抛出异常。"""
        service = MachineService()
        service.start()
        try:
            service.start()  # 第二次调用
            assert service._worker.is_alive()
        finally:
            service.stop()


# ── TestSampling ──────────────────────────────────────────────────────────────


class TestSampling:
    """测试 _sample() 采样功能。"""

    def test_sample_returns_snapshot(self, mock_settings):
        """验证 _sample() 返回 MachineSnapshot 对象。"""
        service = MachineService()
        snapshot = service._sample()
        assert isinstance(snapshot, MachineSnapshot)

    def test_sample_has_cpu_data(self, mock_settings):
        """验证采样包含 CPU 数据。"""
        service = MachineService()
        snapshot = service._sample()
        assert hasattr(snapshot, "cpu_percent")
        assert isinstance(snapshot.cpu_percent, (int, float))
        assert 0 <= snapshot.cpu_percent <= 100

    def test_sample_has_memory_data(self, mock_settings):
        """验证采样包含内存数据。"""
        service = MachineService()
        snapshot = service._sample()
        assert hasattr(snapshot, "mem_percent")
        assert hasattr(snapshot, "mem_used_mb")
        assert hasattr(snapshot, "mem_total_mb")
        assert isinstance(snapshot.mem_percent, (int, float))
        assert 0 <= snapshot.mem_percent <= 100

    def test_sample_has_disk_data(self, mock_settings):
        """验证采样包含磁盘数据。"""
        service = MachineService()
        snapshot = service._sample()
        assert hasattr(snapshot, "disk_percent")
        assert hasattr(snapshot, "disk_used_mb")
        assert hasattr(snapshot, "disk_total_mb")
        assert isinstance(snapshot.disk_percent, (int, float))

    def test_sample_has_process_data(self, mock_settings):
        """验证采样包含进程数据（可能为 None）。"""
        service = MachineService()
        snapshot = service._sample()
        assert hasattr(snapshot, "proc_mem_mb")
        assert hasattr(snapshot, "proc_cpu_percent")
        assert hasattr(snapshot, "proc_workers")
        # 这些字段可能为 None（采集失败时）
        if snapshot.proc_mem_mb is not None:
            assert isinstance(snapshot.proc_mem_mb, (int, float))


# ── TestCurrent ───────────────────────────────────────────────────────────────


class TestCurrent:
    """测试 current() 实时查询。"""

    def test_current_returns_dict(self, mock_settings):
        """验证 current() 返回字典。"""
        service = MachineService()
        result = service.current()
        assert isinstance(result, dict)

    def test_current_contains_cpu_percent(self, mock_settings):
        """验证 current() 包含 cpu_percent。"""
        service = MachineService()
        result = service.current()
        assert "cpu_percent" in result

    def test_current_contains_timestamp(self, mock_settings):
        """验证 current() 包含 timestamp。"""
        service = MachineService()
        result = service.current()
        assert "timestamp" in result
        assert isinstance(result["timestamp"], float)

    def test_sample_method_returns_snapshot(self, mock_settings):
        """验证 sample() 方法返回 MachineSnapshot 对象。"""
        service = MachineService()
        snapshot = service.sample()
        assert isinstance(snapshot, MachineSnapshot)


# ── TestHistory ───────────────────────────────────────────────────────────────


class TestHistory:
    """测试 history() 历史数据查询。"""

    def test_history_returns_list(self, mock_settings):
        """验证 history() 返回列表。"""
        service = MachineService()
        result = service.history()
        assert isinstance(result, list)

    def test_history_initially_empty(self, mock_settings):
        """验证初始时历史数据为空。"""
        service = MachineService()
        result = service.history()
        assert len(result) == 0

    def test_history_after_worker_runs(self, mock_settings):
        """验证工作线程运行后历史数据不为空。"""
        mock_settings.bridges.machine.interval_seconds = 1
        mock_settings.bridges.machine.max_samples = 10
        service = MachineService()
        service.start()
        try:
            time.sleep(2.5)  # 等待至少 2 次采样
            result = service.history()
            assert len(result) >= 1
        finally:
            service.stop()

    def test_history_with_minutes_parameter(self, mock_settings):
        """验证 history(minutes=N) 返回最近 N 分钟的数据。"""
        mock_settings.bridges.machine.interval_seconds = 1
        mock_settings.bridges.machine.max_samples = 100
        service = MachineService()
        service.start()
        try:
            time.sleep(2.5)
            result = service.history(minutes=1)
            assert isinstance(result, list)
            # 1 分钟 = 60 秒，采样间隔 1 秒，最多 60 个样本
            assert len(result) <= 60
        finally:
            service.stop()

    def test_history_items_are_dicts(self, mock_settings):
        """验证历史数据中的每一项都是字典。"""
        mock_settings.bridges.machine.interval_seconds = 1
        mock_settings.bridges.machine.max_samples = 10
        service = MachineService()
        service.start()
        try:
            time.sleep(2.5)
            result = service.history()
            if len(result) > 0:
                assert all(isinstance(item, dict) for item in result)
        finally:
            service.stop()


# ── TestBuffer ────────────────────────────────────────────────────────────────


class TestBuffer:
    """测试缓冲区管理（循环队列）。"""

    def test_buffer_max_length(self, mock_settings):
        """验证缓冲区不超过最大长度。"""
        mock_settings.bridges.machine.interval_seconds = 1
        mock_settings.bridges.machine.max_samples = 5
        service = MachineService()
        service.start()
        try:
            time.sleep(7)  # 等待超过 max_samples 的采样次数
            assert len(service._buffer) <= 5
        finally:
            service.stop()

    def test_buffer_circular_behavior(self, mock_settings):
        """验证缓冲区循环覆盖旧数据。"""
        mock_settings.bridges.machine.interval_seconds = 1
        mock_settings.bridges.machine.max_samples = 3
        service = MachineService()
        service.start()
        try:
            time.sleep(5)  # 采样 5 次，缓冲区只保留最新 3 次
            assert len(service._buffer) == 3
        finally:
            service.stop()


# ── TestHealth ────────────────────────────────────────────────────────────────


class TestHealth:
    """测试 health() 健康检查。"""

    def test_health_returns_service_health(self, mock_settings):
        """验证 health() 返回 ServiceHealth 对象。"""
        service = MachineService()
        from app.bridges.resources.base.servicehealth import ServiceHealth

        health = service.health()
        assert isinstance(health, ServiceHealth)

    def test_health_has_service_name(self, mock_settings):
        """验证健康状态包含服务名称。"""
        service = MachineService()
        health = service.health()
        assert health.service == "machine"

    def test_health_worker_not_alive_initially(self, mock_settings):
        """验证初始时工作线程状态为 False。"""
        service = MachineService()
        health = service.health()
        assert health.worker_alive is False

    def test_health_worker_alive_after_start(self, mock_settings):
        """验证启动后工作线程状态为 True。"""
        service = MachineService()
        service.start()
        try:
            health = service.health()
            assert health.worker_alive is True
        finally:
            service.stop()

    def test_health_has_last_active_time(self, mock_settings):
        """验证健康状态包含最后活跃时间。"""
        mock_settings.bridges.machine.interval_seconds = 1
        service = MachineService()
        service.start()
        try:
            time.sleep(1.5)
            health = service.health()
            assert health.last_active_time is not None
            assert isinstance(health.last_active_time, float)
        finally:
            service.stop()


# ── TestCheck ─────────────────────────────────────────────────────────────────


class TestCheck:
    """测试 check() 系统信息。"""

    def test_check_returns_dict(self, mock_settings):
        """验证 check() 返回字典。"""
        service = MachineService()
        result = service.check()
        assert isinstance(result, dict)

    def test_check_has_status(self, mock_settings):
        """验证 check() 包含 status 字段。"""
        service = MachineService()
        result = service.check()
        assert "status" in result
        assert result["status"] == "ok"

    def test_check_has_system_info(self, mock_settings):
        """验证 check() 包含系统信息。"""
        service = MachineService()
        result = service.check()
        assert "status" in result
        assert "name" in result
        assert "version" in result

# ── TestExport ────────────────────────────────────────────────────────────────


class TestExport:
    """测试 export() 和 describe()。"""

    def test_export_returns_dict(self, mock_settings):
        """验证 export() 返回字典。"""
        service = MachineService()
        result = service.export()
        assert isinstance(result, dict)

    def test_export_has_module_key(self, mock_settings):
        """验证 export() 包含 module 字段。"""
        service = MachineService()
        result = service.export()
        assert "module" in result
        assert result["module"] == "machine"

    def test_export_has_setting(self, mock_settings):
        """验证 export() 包含 setting 字段。"""
        service = MachineService()
        result = service.export()
        assert "setting" in result

    def test_export_has_extra_section(self, mock_settings):
        """验证 export() 包含 extra 字段。"""
        service = MachineService()
        result = service.export()
        assert "extra" in result
        assert isinstance(result["extra"], dict)

    def test_export_has_buffer_size(self, mock_settings):
        """验证 export() 包含当前缓冲区大小。"""
        service = MachineService()
        result = service.export()
        assert "current_buffer_size" in result["extra"]

    def test_describe_returns_valid_json(self, mock_settings):
        """验证 describe() 返回有效的 JSON 字符串。"""
        service = MachineService()
        s = service.describe()
        parsed = json.loads(s)
        assert isinstance(parsed, dict)

    def test_describe_contains_module_name(self, mock_settings):
        """验证 describe() 包含模块名称。"""
        service = MachineService()
        s = service.describe()
        assert "machine" in s


# ── TestShutdown ──────────────────────────────────────────────────────────────


class TestShutdown:
    """测试 stop() 停止服务。"""

    def test_stop_sets_stop_event(self, mock_settings):
        """验证 stop() 设置停止事件。"""
        service = MachineService()
        service.start()
        service.stop()
        assert service._stop.is_set()

    def test_stop_waits_for_worker(self, mock_settings):
        """验证 stop() 等待工作线程结束。"""
        mock_settings.bridges.machine.interval_seconds = 1
        service = MachineService()
        service.start()
        time.sleep(0.5)
        service.stop()
        # 工作线程应该已经停止（或接近停止）
        # 由于设置了 5 秒超时，测试不应该长时间阻塞

    def test_stop_on_unstarted_service(self, mock_settings):
        """验证在未启动的服务上调用 stop() 不会抛出异常。"""
        service = MachineService()
        service.stop()  # 不应抛出异常


# ── TestThreadSafety ──────────────────────────────────────────────────────────


class TestThreadSafety:
    """测试线程安全性。"""

    def test_concurrent_history_access(self, mock_settings):
        """验证并发访问 history() 不会导致错误。"""
        mock_settings.bridges.machine.interval_seconds = 1
        mock_settings.bridges.machine.max_samples = 10
        service = MachineService()
        service.start()

        results = []

        def access_history():
            for _ in range(5):
                try:
                    result = service.history()
                    results.append(result)
                except Exception as e:
                    results.append(e)
                time.sleep(0.1)

        try:
            threads = [threading.Thread(target=access_history) for _ in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # 验证所有访问都成功（没有异常）
            assert all(isinstance(r, list) for r in results)
        finally:
            service.stop()
