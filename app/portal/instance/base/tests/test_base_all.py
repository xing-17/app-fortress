"""
综合测试：app.portal.instance.base

覆盖范围
--------
- TestBaseInstanceState     枚举值正确性；字符串序列化
- TestInstanceLike          Protocol 类型提示约束
- TestBaseInstance          抽象方法强制实现；状态管理；启动/停止流程；错误回滚；导出功能
"""

from __future__ import annotations

import pytest

from app.common.setting.portal import BaseInstanceSetting
from app.portal.instance.base.base import (
    BaseInstance,
    BaseInstanceState,
    InstanceLike,
)

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures & Helpers
# ──────────────────────────────────────────────────────────────────────────────


class DummyInstance(BaseInstance):
    """测试用具体实现类。"""

    def __init__(self, setting: BaseInstanceSetting, should_fail: bool = False):
        super().__init__(setting)
        self.should_fail = should_fail
        self.load_called = False
        self.ping_called = False
        self.start_called = False
        self.stop_called = False
        self.command_history: list[str] = []

    def load(self) -> None:
        self.load_called = True
        self.spec = {"type": "dummy", "cpu": 2}
        self.state = BaseInstanceState.STOPPED

    def ping(self) -> bool:
        self.ping_called = True
        return not self.should_fail

    def get_state(self) -> BaseInstanceState:
        return self.state

    def _start_instance(self) -> None:
        if self.should_fail:
            raise RuntimeError("Simulated start failure")
        self.start_called = True

    def _wait_for_start(self) -> None:
        pass

    def _stop_instance(self) -> None:
        if self.should_fail:
            raise RuntimeError("Simulated stop failure")
        self.stop_called = True

    def _wait_for_stop(self) -> None:
        pass

    def _load_specification(self) -> dict:
        return {"type": "dummy", "cpu": 2, "memory": 4}

    def run_command(
        self,
        command: str,
        timeout: int = 300,
        wait: bool = True,
    ) -> dict:
        self.command_history.append(command)
        return {"command": command, "status": "success"}


@pytest.fixture
def instance_setting():
    return BaseInstanceSetting(
        type="test",
        name="test-instance",
        key="test-key-12345",
        host="192.168.1.100",
        port=22,
        timeout=30,
    )


@pytest.fixture
def dummy_instance(instance_setting):
    return DummyInstance(setting=instance_setting)


@pytest.fixture
def failing_instance(instance_setting):
    return DummyInstance(setting=instance_setting, should_fail=True)


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseInstanceState
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseInstanceState:
    def test_enum_values_are_correct(self):
        assert BaseInstanceState.UNKNOWN.value == "unknown"
        assert BaseInstanceState.PENDING.value == "pending"
        assert BaseInstanceState.RUNNING.value == "running"
        assert BaseInstanceState.STARTING.value == "starting"
        assert BaseInstanceState.STOPPED.value == "stopped"
        assert BaseInstanceState.STOPPING.value == "stopping"
        assert BaseInstanceState.ERROR.value == "error"

    def test_enum_is_str_subclass(self):
        assert isinstance(BaseInstanceState.RUNNING, str)
        assert BaseInstanceState.RUNNING == "running"

    def test_enum_serialization(self):
        import json

        data = {"state": BaseInstanceState.RUNNING.value}
        serialized = json.dumps(data)
        assert "running" in serialized


# ──────────────────────────────────────────────────────────────────────────────
# TestInstanceLike
# ──────────────────────────────────────────────────────────────────────────────


class TestInstanceLike:
    def test_protocol_type_hint_works(self):
        """InstanceLike 作为 Protocol 可用于类型提示。"""

        def accept_instance(instance: InstanceLike) -> bool:
            return instance.ping()

        dummy = DummyInstance(
            BaseInstanceSetting(
                type="test",
                name="test",
                key="test-key",
                host="127.0.0.1",
                port=22,
                timeout=10,
            )
        )
        result = accept_instance(dummy)
        assert isinstance(result, bool)


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseInstance
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseInstance:
    def test_init_sets_attributes_from_setting(self, dummy_instance, instance_setting):
        assert dummy_instance.setting == instance_setting
        assert dummy_instance.name == "test-instance"
        assert dummy_instance.state == BaseInstanceState.UNKNOWN
        assert dummy_instance.spec == {}

    def test_abstract_methods_must_be_implemented(self, instance_setting):
        """BaseInstance 无法直接实例化，必须实现抽象方法。"""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseInstance(setting=instance_setting)

    def test_set_state_changes_state(self, dummy_instance):
        dummy_instance._set_state(BaseInstanceState.RUNNING)
        assert dummy_instance.state == BaseInstanceState.RUNNING

    def test_unset_state_resets_to_unknown(self, dummy_instance):
        dummy_instance._set_state(BaseInstanceState.RUNNING)
        dummy_instance._unset_state()
        assert dummy_instance.state == BaseInstanceState.UNKNOWN

    def test_is_running_property(self, dummy_instance):
        assert not dummy_instance.is_running
        dummy_instance._set_state(BaseInstanceState.RUNNING)
        assert dummy_instance.is_running

    def test_is_stopped_property(self, dummy_instance):
        assert not dummy_instance.is_stopped
        dummy_instance._set_state(BaseInstanceState.STOPPED)
        assert dummy_instance.is_stopped

    def test_start_success_changes_state_to_running(self, dummy_instance):
        dummy_instance.start()
        assert dummy_instance.state == BaseInstanceState.RUNNING
        assert dummy_instance.start_called

    def test_start_failure_resets_state(self, failing_instance):
        with pytest.raises(RuntimeError, match="Simulated start failure"):
            failing_instance.start()
        assert failing_instance.state == BaseInstanceState.UNKNOWN

    def test_stop_success_changes_state_to_stopped(self, dummy_instance):
        dummy_instance._set_state(BaseInstanceState.RUNNING)
        dummy_instance.stop()
        assert dummy_instance.state == BaseInstanceState.STOPPED
        assert dummy_instance.stop_called

    def test_stop_failure_resets_state(self, failing_instance):
        failing_instance._set_state(BaseInstanceState.RUNNING)
        with pytest.raises(RuntimeError, match="Simulated stop failure"):
            failing_instance.stop()
        assert failing_instance.state == BaseInstanceState.UNKNOWN

    def test_restart_calls_stop_then_start(self, dummy_instance):
        dummy_instance._set_state(BaseInstanceState.RUNNING)
        dummy_instance.restart()
        assert dummy_instance.stop_called
        assert dummy_instance.start_called
        assert dummy_instance.state == BaseInstanceState.RUNNING

    def test_ping_calls_implementation(self, dummy_instance):
        result = dummy_instance.ping()
        assert result is True
        assert dummy_instance.ping_called

    def test_get_specification_returns_spec(self, dummy_instance):
        spec = dummy_instance.get_specification()
        assert spec == {"type": "dummy", "cpu": 2, "memory": 4}

    def test_run_command_returns_result(self, dummy_instance):
        result = dummy_instance.run_command("echo test", timeout=100, wait=True)
        assert result == {"command": "echo test", "status": "success"}
        assert "echo test" in dummy_instance.command_history

    def test_export_returns_complete_snapshot(self, dummy_instance):
        dummy_instance._set_state(BaseInstanceState.RUNNING)
        dummy_instance.spec = {"cpu": 4}
        exported = dummy_instance.export()

        assert exported["name"] == "test-instance"
        assert exported["host"] == "192.168.1.100"
        assert exported["port"] == 22
        assert exported["timeout"] == 30
        assert exported["state"] == "running"
        assert exported["is_running"] is True
        assert exported["is_stopped"] is False
        assert exported["spec"] == {"cpu": 4}
