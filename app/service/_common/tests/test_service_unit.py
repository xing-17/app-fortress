from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

from app.internal.constant.servicekind import ServiceKind
from app.internal.constant.servicestate import ServiceState
from app.internal.logstream import LogStream
from app.resource._global.logstreams import GlobalLogStreams
from app.service._common import BaseService
from app.setting.service import NodeServiceSetting


class _FakeService(BaseService[NodeServiceSetting]):
    kind = ServiceKind.NODE

    def __init__(self, setting: NodeServiceSetting) -> None:
        super().__init__(setting)
        self.started = 0
        self.stopped = 0
        self.start_error: BaseException | None = None
        self.stop_error: BaseException | None = None

    def _start(self) -> None:
        self.started += 1
        if self.start_error:
            raise self.start_error

    def _stop(self) -> None:
        self.stopped += 1
        if self.stop_error:
            raise self.stop_error


@pytest.fixture(autouse=True)
def _fake_log(monkeypatch):
    # Avoid creating real log files under ./local/.logs.
    _log = MagicMock(spec=LogStream)
    monkeypatch.setattr(GlobalLogStreams, "resolve", lambda value, default: _log)
    return _log


@pytest.fixture
def service() -> _FakeService:
    return _FakeService(NodeServiceSetting())


class TestInit:
    def test_initial_state_is_created(self, service):
        assert service.state == ServiceState.CREATED

    def test_exposes_setting_and_log(self, service, _fake_log):
        assert service.setting.kind == ServiceKind.NODE
        assert service.log is _fake_log

    def test_kind_mismatch_raises(self):
        class _Other(_FakeService):
            kind = ServiceKind.MCPHOST

        with pytest.raises(ValueError, match="requires a mcphost setting"):
            _Other(NodeServiceSetting())

    def test_abstract_hooks_required(self):
        with pytest.raises(TypeError):
            BaseService(NodeServiceSetting())  # type: ignore[abstract]


class TestStart:
    def test_start_runs_hook_and_becomes_running(self, service):
        service.start()
        assert service.state == ServiceState.RUNNING
        assert service.started == 1

    def test_start_when_running_is_noop(self, service):
        service.start()
        service.start()
        assert service.started == 1

    def test_start_failure_sets_failed_and_reraises(self, service):
        service.start_error = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            service.start()
        assert service.state == ServiceState.FAILED

    def test_start_failure_catches_base_exception(self, service):
        service.start_error = KeyboardInterrupt()
        with pytest.raises(KeyboardInterrupt):
            service.start()
        assert service.state == ServiceState.FAILED

    def test_start_from_failed_raises(self, service):
        service.start_error = RuntimeError("boom")
        with pytest.raises(RuntimeError):
            service.start()
        service.start_error = None
        with pytest.raises(RuntimeError, match="cannot start from state failed"):
            service.start()
        assert service.started == 1

    def test_restart_after_stop(self, service):
        service.start()
        service.stop()
        service.start()
        assert service.state == ServiceState.RUNNING
        assert service.started == 2


class TestStop:
    def test_stop_runs_hook_and_becomes_stopped(self, service):
        service.start()
        service.stop()
        assert service.state == ServiceState.STOPPED
        assert service.stopped == 1

    def test_stop_when_created_is_noop(self, service):
        service.stop()
        assert service.state == ServiceState.CREATED
        assert service.stopped == 0

    def test_stop_when_stopped_is_noop(self, service):
        service.start()
        service.stop()
        service.stop()
        assert service.stopped == 1

    def test_stop_failure_sets_failed_and_reraises(self, service):
        service.start()
        service.stop_error = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            service.stop()
        assert service.state == ServiceState.FAILED

    def test_stop_from_failed_runs_hook(self, service):
        service.start_error = RuntimeError("boom")
        with pytest.raises(RuntimeError):
            service.start()
        service.stop()
        assert service.state == ServiceState.STOPPED
        assert service.stopped == 1


class TestTransientStates:
    def test_state_is_starting_inside_start_hook(self, service):
        _seen: list[ServiceState] = []
        service._start = lambda: _seen.append(service.state)
        service.start()
        assert _seen == [ServiceState.STARTING]

    def test_state_is_stopping_inside_stop_hook(self, service):
        _seen: list[ServiceState] = []
        service.start()
        service._stop = lambda: _seen.append(service.state)
        service.stop()
        assert _seen == [ServiceState.STOPPING]

    def test_stop_during_start_raises(self, service):
        _errors: list[Exception] = []

        def _hook() -> None:
            try:
                service.stop()
            except RuntimeError as e:
                _errors.append(e)

        service._start = _hook
        service.start()
        assert len(_errors) == 1
        assert "cannot stop from state starting" in str(_errors[0])

    def test_start_during_stop_raises(self, service):
        _errors: list[Exception] = []
        service.start()

        def _hook() -> None:
            try:
                service.start()
            except RuntimeError as e:
                _errors.append(e)

        service._stop = _hook
        service.stop()
        assert len(_errors) == 1
        assert "cannot start from state stopping" in str(_errors[0])


class TestTransitionLogging:
    def test_logs_each_transition(self, service, _fake_log):
        service.start()
        service.stop()
        _messages = [c.args[0] for c in _fake_log.info.call_args_list]
        assert _messages == [
            "node: created -> starting",
            "node: starting -> running",
            "node: running -> stopping",
            "node: stopping -> stopped",
        ]

    def test_failure_logs_exception(self, service, _fake_log):
        service.start_error = RuntimeError("boom")
        with pytest.raises(RuntimeError):
            service.start()
        _fake_log.exception.assert_called_once_with("node: start failed")


class TestHealth:
    def test_health_reports_kind_state_and_running(self, service):
        assert service.health() == {"kind": "node", "state": "created", "is_running": False}
        service.start()
        assert service.health() == {"kind": "node", "state": "running", "is_running": True}

    def test_is_running_follows_state(self, service):
        assert service.is_running is False
        service.start()
        assert service.is_running is True
        service.stop()
        assert service.is_running is False


class TestConcurrency:
    def test_concurrent_start_runs_hook_once(self, service):
        _barrier = threading.Barrier(8)

        def _run() -> None:
            _barrier.wait()
            service.start()

        _threads = [threading.Thread(target=_run) for _ in range(8)]
        for t in _threads:
            t.start()
        for t in _threads:
            t.join()
        assert service.started == 1
        assert service.state == ServiceState.RUNNING
