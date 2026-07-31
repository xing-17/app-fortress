"""
补充测试：覆盖 service.py 中未测试的边界情况

覆盖范围
--------
- TestLoadResources         测试 _load_resources 方法（line 111）
- TestHealthEdgeCases       测试 health() 方法的边界情况（lines 263-268）
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, ClassVar

import pytest

from app.bridges.base.registry import BaseRegistry
from app.bridges.base.service import BaseBridgesService
from app.bridges.base.state import BaseBridgesState, BaseBridgesStatus
from app.common.context.base import BaseContext

# ── 测试用具体类 ──────────────────────────────────────────────────────────────


class DummyRequest(BaseContext):
    """测试用请求类。"""

    id_prefix: ClassVar[str] = "req"
    id_length: ClassVar[int] = 8


@dataclass(kw_only=True)
class DummyState(BaseBridgesState):
    """测试用状态类。"""

    request: DummyRequest
    type: str = "dummy_state"

    def export(self) -> dict[str, Any]:
        result = super().export()
        result["request_id"] = self.request.id
        return result


class DummyService(BaseBridgesService[DummyRequest, DummyState]):
    """测试用 Service。"""

    def __init__(self, registry: BaseRegistry) -> None:
        self._test_registry = registry
        super().__init__()

    @property
    def module_name(self) -> str:
        return "dummy"

    def _load_registry(self) -> BaseRegistry:
        return self._test_registry

    def _get_queue_size_limit(self) -> int:
        return 10

    def _get_worker_name(self) -> str:
        return "DummyWorker"

    def _create_initial_state(self, request: DummyRequest) -> DummyState:
        return DummyState(request=request)

    def run(self, request: DummyRequest) -> DummyState:
        state = DummyState(request=request)
        state.status = BaseBridgesStatus.DONE
        return state

    def cancel(self, request_id: str) -> None:
        with self._live_lock:
            state = self._live.get(request_id)
            if state and state.status == BaseBridgesStatus.PENDING:
                state.cancel()


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def registry(tmp_path):
    """创建测试用注册表。"""
    path = tmp_path / "test_registry.json"
    reg = BaseRegistry("test", str(path))
    reg.load()
    return reg


@pytest.fixture
def service(registry):
    """创建测试用服务。"""
    return DummyService(registry)


# ──────────────────────────────────────────────────────────────────────────────
# TestLoadResources
# ──────────────────────────────────────────────────────────────────────────────


class TestLoadResources:
    """测试 _load_resources 方法"""

    def test_load_resources_returns_module_warehouse(self, service):
        """测试 _load_resources 返回 ModuleBridgesWarehouse"""
        from app.bridges.resources._warehouse.warehouse import ModuleBridgesWarehouse

        # 调用 _load_resources
        result = service._load_resources()

        # 验证返回值
        assert result is ModuleBridgesWarehouse

    def test_resources_attribute_uses_load_resources(self, service):
        """测试 resources 属性使用了 _load_resources 的结果"""
        from app.bridges.resources._warehouse.warehouse import ModuleBridgesWarehouse

        assert service.resources is ModuleBridgesWarehouse


# ──────────────────────────────────────────────────────────────────────────────
# TestHealthEdgeCases
# ──────────────────────────────────────────────────────────────────────────────


class TestHealthEdgeCases:
    """测试 health() 方法的边界情况"""

    def test_health_returns_service_health_instance(self, service):
        """测试 health() 返回 ServiceHealth 实例"""
        from app.bridges.base.servicehealth import ServiceHealth

        health = service.health()
        assert isinstance(health, ServiceHealth)

    def test_health_includes_worker_native_id(self, service):
        """测试 health() 包含 worker_native_id"""
        service.start()

        health = service.health()

        # worker_native_id 应该在线程启动后存在
        assert hasattr(health, "worker_native_id")
        # 由于线程已启动，native_id 应该是一个整数
        if service._worker.is_alive():
            assert isinstance(health.worker_native_id, (int, type(None)))

        service.stop()

    def test_health_worker_native_id_before_start(self, service):
        """测试启动前 worker_native_id 为 None"""
        health = service.health()

        # 线程未启动时，native_id 应该是 None
        assert health.worker_native_id is None

    def test_health_worker_native_id_after_start(self, service):
        """测试启动后 worker_native_id 被设置（可能为 None）"""
        service.start()
        # 等待线程真正启动
        import time

        time.sleep(0.1)

        health = service.health()

        # 线程启动后，native_id 可能是一个正整数或 None（取决于 Python 版本和平台）
        if hasattr(service._worker, "native_id") and service._worker.is_alive():
            # native_id 可能为 None 或正整数
            assert health.worker_native_id is None or (
                isinstance(health.worker_native_id, int) and health.worker_native_id > 0
            )

        service.stop()

    def test_health_worker_ident_matches_thread_ident(self, service):
        """测试 health 中的 worker_ident 与实际线程 ident 匹配"""
        service.start()

        health = service.health()

        # worker_ident 应该匹配线程的 ident
        assert health.worker_ident == service._worker.ident

        service.stop()

    def test_health_worker_count_includes_current_threads(self, service):
        """测试 health 中的 worker_count 包含当前活跃线程"""
        initial_count = threading.active_count()

        service.start()
        health = service.health()

        # 启动服务后线程数应该增加
        assert health.worker_count >= initial_count

        service.stop()

    def test_health_all_fields_populated_when_running(self, service):
        """测试运行时所有字段都被正确填充"""
        service.start()

        health = service.health()

        # 验证所有关键字段
        assert health.service == "dummy"
        assert health.worker_name == "DummyWorker"
        assert health.worker_alive is True
        assert health.worker_daemon is True
        assert health.worker_ident is not None
        assert health.worker_count > 0
        assert health.queue_size == 0
        assert health.queue_limit == 10
        assert health.queue_full is False

        service.stop()

    def test_health_queue_full_when_at_limit(self, service, registry):
        """测试队列满时 queue_full 为 True"""
        # 不启动 worker，这样请求会堆积
        # 填满队列
        for i in range(10):
            req = DummyRequest()
            service.submit(req)

        health = service.health()

        # 队列应该已满
        assert health.queue_size == 10
        assert health.queue_limit == 10
        assert health.queue_full is True

    def test_health_last_active_time_updates(self, service):
        """测试 last_active_time 在任务处理后更新"""
        service.start()

        # 初始状态 last_active_time 可能为 None
        health1 = service.health()
        initial_time = health1.last_active_time

        # 提交一个请求
        req = DummyRequest()
        service.submit(req)
        service.stop()  # 等待处理完成

        # 重新启动并检查
        service.start()
        health2 = service.health()

        # last_active_time 应该被设置了
        assert health2.last_active_time is not None
        if initial_time is not None:
            # 如果之前有值，新值应该不同（时间推进了）
            assert health2.last_active_time >= initial_time

        service.stop()

    def test_health_export_contains_all_fields(self, service):
        """测试 health.export() 包含所有字段"""
        service.start()

        health = service.health()
        exported = health.export()

        # 验证导出的字典包含所有关键字段
        assert "service" in exported
        assert "worker" in exported
        assert "queue" in exported
        assert "last_active_time" in exported
        assert "idle_seconds" in exported

        # 验证嵌套字段
        assert "name" in exported["worker"]
        assert "alive" in exported["worker"]
        assert "daemon" in exported["worker"]
        assert "ident" in exported["worker"]
        assert "native_id" in exported["worker"]
        assert "count" in exported["worker"]

        assert "size" in exported["queue"]
        assert "limit" in exported["queue"]
        assert "full" in exported["queue"]
        assert "usage" in exported["queue"]

        service.stop()
