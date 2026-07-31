"""
综合测试：app.bridges.base.service

覆盖范围
--------
- TestInstantiation    基本实例化和属性验证
- TestStartWorker      start() 启动工作线程
- TestSubmit           submit() 异步提交任务
- TestLookup           lookup() 查询任务状态
- TestCancel           cancel() 取消排队中的请求
- TestWorkerLoop       worker loop 成功/失败/取消路径
- TestGetQueueSize     get_queue_size() 队列大小
- TestShutdown         stop() 等待队列排空
- TestExport           export() / describe()
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any, ClassVar
from unittest.mock import Mock, patch

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
    """run() 返回 DONE 的测试用 Service。"""

    def __init__(self, registry: BaseRegistry) -> None:
        self._test_registry = registry
        super().__init__()

    @property
    def module_name(self) -> str:
        return "dummy"

    def _load_resources(self) -> Mock:
        return Mock()

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


class DummyFailingService(DummyService):
    """run() 始终抛出异常的测试用 Service。"""

    def run(self, request: DummyRequest) -> DummyState:
        raise RuntimeError("Intentional test error")


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_registry(tmp_path):
    return BaseRegistry("test", str(tmp_path / "registry.json"))


@pytest.fixture
def service(tmp_registry):
    with patch("app.bridges.base.service.GlobalSetting"):
        svc = DummyService(registry=tmp_registry)
    return svc


@pytest.fixture
def failing_service(tmp_path):
    reg = BaseRegistry("test_fail", str(tmp_path / "fail_registry.json"))
    with patch("app.bridges.base.service.GlobalSetting"):
        svc = DummyFailingService(registry=reg)
    return svc


# ── TestInstantiation ─────────────────────────────────────────────────────────


class TestInstantiation:
    """测试基本实例化和属性验证。"""

    def test_has_live_dict(self, service):
        assert isinstance(service._live, dict)
        assert len(service._live) == 0

    def test_has_live_lock(self, service):
        assert isinstance(service._live_lock, type(threading.Lock()))

    def test_has_registry(self, service):
        assert service._registry is not None

    def test_has_queue(self, service):
        assert service._queue is not None

    def test_has_worker_thread(self, service):
        assert isinstance(service._worker, threading.Thread)

    def test_worker_not_alive_before_start(self, service):
        """worker 在 start() 调用前不应处于运行状态。"""
        assert not service._worker.is_alive()

    def test_has_queue_size_limit(self, service):
        assert service._queue_size_limit == 10

    def test_module_name(self, service):
        assert service.module_name == "dummy"


# ── TestStartWorker ───────────────────────────────────────────────────────────


class TestStartWorker:
    """测试 start() 启动工作线程。"""

    def test_start_worker_makes_thread_alive(self, service):
        service.start()
        assert service._worker.is_alive()

    def test_worker_is_daemon(self, service):
        service.start()
        assert service._worker.daemon is True

    def test_start_worker_idempotent(self, service):
        """多次调用 start() 不应抛出异常，线程仍存活。"""
        service.start()
        service.start()
        assert service._worker.is_alive()


# ── TestSubmit ────────────────────────────────────────────────────────────────


class TestSubmit:
    """测试 submit() 异步提交任务。"""

    def test_submit_returns_request_id(self, service):
        req = DummyRequest()
        rid = service.submit(req)
        assert rid == req.id

    def test_submit_id_starts_with_prefix(self, service):
        req = DummyRequest()
        rid = service.submit(req)
        assert rid.startswith("req-")

    def test_submit_adds_initial_state_to_live(self, service):
        req = DummyRequest()
        rid = service.submit(req)
        with service._live_lock:
            assert rid in service._live

    def test_submit_initial_state_is_pending(self, service):
        req = DummyRequest()
        rid = service.submit(req)
        with service._live_lock:
            state = service._live[rid]
        assert state.status == BaseBridgesStatus.PENDING

    def test_submit_increments_queue_size(self, service):
        """worker 未启动时，submit 后队列大小应增加。"""
        req = DummyRequest()
        service.submit(req)
        assert service.get_queue_size() >= 1


# ── TestLookup ────────────────────────────────────────────────────────────────


class TestLookup:
    """测试 lookup() 查询任务状态。"""

    def test_lookup_live_returns_dict(self, service):
        req = DummyRequest()
        rid = service.submit(req)
        result = service.lookup(rid)
        assert isinstance(result, dict)

    def test_lookup_live_pending_status(self, service):
        req = DummyRequest()
        rid = service.submit(req)
        result = service.lookup(rid)
        assert result["status"] == "PENDING"

    def test_lookup_registry_after_completion(self, service):
        """任务完成后，lookup() 应从 registry 返回 DONE 状态。"""
        req = DummyRequest()
        rid = service.submit(req)
        service.start()
        service.stop()
        result = service.lookup(rid)
        assert isinstance(result, dict)
        assert result["status"] == "DONE"

    def test_lookup_not_found_raises_value_error(self, service):
        with pytest.raises(ValueError, match="No state found"):
            service.lookup("nonexistent-id")


# ── TestCancel ────────────────────────────────────────────────────────────────


class TestCancel:
    """测试 cancel() 取消排队中的请求。"""

    def test_cancel_pending_marks_canceled(self, service):
        req = DummyRequest()
        rid = service.submit(req)
        service.cancel(rid)
        with service._live_lock:
            state = service._live.get(rid)
        assert state is not None
        assert state.status == BaseBridgesStatus.CANCELED

    def test_cancel_nonexistent_no_error(self, service):
        """取消不存在的 request_id 不应抛出异常。"""
        service.cancel("nonexistent-id")  # should not raise


# ── TestWorkerLoop ────────────────────────────────────────────────────────────


class TestWorkerLoop:
    """测试 worker loop 的不同执行路径。"""

    def test_successful_run_persists_done_state(self, service):
        """run() 成功时，状态应以 DONE 持久化到 registry。"""
        req = DummyRequest()
        rid = service.submit(req)
        service.start()
        service.stop()
        result = service.lookup(rid)
        assert result["status"] == "DONE"

    def test_successful_run_clears_live(self, service):
        """run() 完成后，_live 中的条目应被清除。"""
        req = DummyRequest()
        rid = service.submit(req)
        service.start()
        service.stop()
        with service._live_lock:
            assert rid not in service._live

    def test_failed_run_persists_failed_state(self, failing_service):
        """run() 抛出异常时，状态应以 FAILED 持久化到 registry。"""
        req = DummyRequest()
        rid = failing_service.submit(req)
        failing_service.start()
        failing_service.stop()
        result = failing_service.lookup(rid)
        assert result["status"] == "FAILED"

    def test_failed_run_clears_live(self, failing_service):
        """run() 抛出异常后，_live 中的条目应被清除。"""
        req = DummyRequest()
        rid = failing_service.submit(req)
        failing_service.start()
        failing_service.stop()
        with failing_service._live_lock:
            assert rid not in failing_service._live

    def test_cancelled_request_persists_canceled_state(self, service):
        """worker 跳过已取消的请求，状态应以 CANCELED 持久化到 registry。"""
        req = DummyRequest()
        rid = service.submit(req)
        service.cancel(rid)
        service.start()
        service.stop()
        result = service.lookup(rid)
        assert result["status"] == "CANCELED"

    def test_cancelled_request_clears_live(self, service):
        """worker 跳过已取消的请求后，_live 中的条目应被清除。"""
        req = DummyRequest()
        rid = service.submit(req)
        service.cancel(rid)
        service.start()
        service.stop()
        with service._live_lock:
            assert rid not in service._live

    def test_multiple_requests_all_processed(self, service):
        """多个请求均应被正确处理并持久化到 registry。"""
        requests = [DummyRequest() for _ in range(5)]
        rids = [service.submit(req) for req in requests]
        service.start()
        service.stop()
        for rid in rids:
            result = service.lookup(rid)
            assert result["status"] == "DONE"


# ── TestGetQueueSize ──────────────────────────────────────────────────────────


class TestGetQueueSize:
    """测试 get_queue_size() 队列大小。"""

    def test_queue_size_initially_zero(self, service):
        assert service.get_queue_size() == 0

    def test_queue_size_after_submit_without_worker(self, service):
        """worker 未启动时，submit 后队列大小应等于提交数。"""
        for _ in range(3):
            service.submit(DummyRequest())
        assert service.get_queue_size() == 3

    def test_queue_size_after_shutdown(self, service):
        """stop 后队列大小应为 0。"""
        for _ in range(3):
            service.submit(DummyRequest())
        service.start()
        service.stop()
        assert service.get_queue_size() == 0


# ── TestShutdown ──────────────────────────────────────────────────────────────


class TestShutdown:
    """测试 stop() 等待队列排空。"""

    def test_shutdown_drains_queue(self, service):
        """stop() 阻塞直至队列清空，所有请求处理完毕。"""
        for _ in range(5):
            service.submit(DummyRequest())
        service.start()
        service.stop()
        assert service.get_queue_size() == 0

    def test_shutdown_on_empty_queue_returns_immediately(self, service):
        """空队列调用 stop() 应立即返回。"""
        service.start()
        service.stop()  # should not block


# ── TestExport ────────────────────────────────────────────────────────────────


class TestExport:
    """测试 export() 和 describe()。"""

    def test_export_returns_dict(self, service):
        result = service.export()
        assert isinstance(result, dict)

    def test_export_has_module_key(self, service):
        result = service.export()
        assert "module" in result
        assert result["module"] == "dummy"

    def test_export_has_queue_section(self, service):
        result = service.export()
        assert "queue" in result
        assert "max_size" in result["queue"]
        assert "current_size" in result["queue"]

    def test_export_queue_max_size(self, service):
        result = service.export()
        assert result["queue"]["max_size"] == 10

    def test_export_queue_current_size_zero(self, service):
        result = service.export()
        assert result["queue"]["current_size"] == 0

    def test_export_has_live_section(self, service):
        result = service.export()
        assert "live" in result
        assert isinstance(result["live"], dict)

    def test_export_live_reflects_submitted_request(self, service):
        req = DummyRequest()
        rid = service.submit(req)
        result = service.export()
        assert rid in result["live"]

    def test_export_has_registry_section(self, service):
        result = service.export()
        assert "registry" in result

    def test_describe_returns_valid_json(self, service):
        s = service.describe()
        parsed = json.loads(s)
        assert isinstance(parsed, dict)

    def test_describe_contains_module_name(self, service):
        s = service.describe()
        assert "dummy" in s
