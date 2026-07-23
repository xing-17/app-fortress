"""
综合测试：app.portal.instance.ecs.instance

覆盖范围
--------
- TestEcsInstanceState     枚举值继承验证
- TestEcsInstance          实例初始化；状态管理；启动/停止流程；ping连通性；命令执行；导出功能
"""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.common.setting.portal import EcsInstanceSetting
from app.portal.instance.base.base import BaseInstanceState
from app.portal.instance.ecs.instance import EcsInstance, EcsInstanceState

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures & Helpers
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def ecs_setting():
    """ECS 实例配置 fixture。"""
    return EcsInstanceSetting(
        type="ecs",
        name="test-ecs-instance",
        key="test-key-12345",
        host="192.168.1.100",
        port=22,
        timeout=30,
        region="cn-hangzhou",
        access_key_id="test-access-key-id-1234567890",
        access_key_secret="test-access-key-secret-1234567890",
    )


@pytest.fixture
def mock_ecs_instance_client():
    """用于 EcsInstance 的完整 mock fixture。"""
    with patch("app.portal.instance.ecs.instance._EcsClient") as mock_client_class:
        mock_client = MagicMock()

        # 模拟 get_instance 返回
        mock_client.get_instance.return_value = {
            "InstanceId": "i-test123456",
            "Status": "Running",
            "Cpu": 2,
            "Memory": 4096,
        }

        # 模拟状态解析
        mock_client._resolve_instance_state.return_value = "Running"

        # 模拟启动和停止
        mock_client._client.start_instance_with_options.return_value = None
        mock_client.stop_instance.return_value = None
        mock_client.wait_instance.return_value = None

        # 模拟命令执行
        mock_client._start_command.return_value = {
            "CommandId": "c-test123",
            "InvokeId": "i-test123",
        }
        mock_client._wait_command.return_value = None
        mock_client._get_command_result.return_value = {
            "Invocation": {
                "InvocationResults": {
                    "InvocationResult": [
                        {
                            "InvokeRecordStatus": "Finished",
                            "Output": "dGVzdCBvdXRwdXQ=",  # base64 encoded "test output"
                        }
                    ]
                }
            }
        }

        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def ecs_instance(ecs_setting, mock_ecs_instance_client):
    """EcsInstance 实例 fixture。"""
    return EcsInstance(setting=ecs_setting)


# ──────────────────────────────────────────────────────────────────────────────
# TestEcsInstanceState
# ──────────────────────────────────────────────────────────────────────────────


class TestEcsInstanceState:
    """测试 EcsInstanceState 枚举。"""

    def test_ecs_state_inherits_base_state(self):
        """验证 EcsInstanceState 继承自 BaseInstanceState。"""
        assert EcsInstanceState == BaseInstanceState

    def test_enum_values_are_correct(self):
        """验证枚举值的正确性。"""
        assert EcsInstanceState.UNKNOWN.value == "unknown"
        assert EcsInstanceState.PENDING.value == "pending"
        assert EcsInstanceState.RUNNING.value == "running"
        assert EcsInstanceState.STARTING.value == "starting"
        assert EcsInstanceState.STOPPED.value == "stopped"
        assert EcsInstanceState.STOPPING.value == "stopping"
        assert EcsInstanceState.ERROR.value == "error"


# ──────────────────────────────────────────────────────────────────────────────
# TestEcsInstance
# ──────────────────────────────────────────────────────────────────────────────


class TestEcsInstance:
    """测试 EcsInstance 类。"""

    def test_initialization(self, ecs_instance, ecs_setting):
        """测试实例初始化。"""
        assert ecs_instance.setting == ecs_setting
        assert ecs_instance.name == ecs_setting.name
        assert ecs_instance.region_id == ecs_setting.region
        # load 在初始化时被调用
        assert isinstance(ecs_instance.spec, dict)
        assert ecs_instance.state is not None

    def test_load_sets_spec_and_state(self, ecs_instance, mock_ecs_instance_client):
        """测试 load 方法设置 spec 和 state。"""
        ecs_instance.load()
        assert isinstance(ecs_instance.spec, dict)
        assert ecs_instance.state is not None

    def test_ping_success(self, ecs_instance):
        """测试 ping 连通性（成功）。"""
        with patch("socket.create_connection") as mock_socket:
            mock_socket.return_value.__enter__ = Mock()
            mock_socket.return_value.__exit__ = Mock()
            result = ecs_instance.ping()
            assert result is True

    def test_ping_timeout(self, ecs_instance):
        """测试 ping 连通性（超时）。"""
        with patch("socket.create_connection", side_effect=socket.timeout):
            result = ecs_instance.ping()
            assert result is False

    def test_ping_connection_error(self, ecs_instance):
        """测试 ping 连通性（连接错误）。"""
        with patch("socket.create_connection", side_effect=socket.error):
            result = ecs_instance.ping()
            assert result is False

    def test_ping_os_error(self, ecs_instance):
        """测试 ping 连通性（OS错误）。"""
        with patch("socket.create_connection", side_effect=OSError):
            result = ecs_instance.ping()
            assert result is False

    def test_get_state_returns_correct_state(self, ecs_instance, mock_ecs_instance_client):
        """测试获取实例状态。"""
        state = ecs_instance.get_state()
        assert state == EcsInstanceState.RUNNING

    def test_get_state_unknown_when_none(self, ecs_instance, mock_ecs_instance_client):
        """测试状态为 None 时返回 UNKNOWN。"""
        mock_ecs_instance_client._resolve_instance_state.return_value = None
        state = ecs_instance.get_state()
        assert state == EcsInstanceState.UNKNOWN

    def test_get_state_unknown_for_invalid_value(self, ecs_instance, mock_ecs_instance_client):
        """测试无效状态值时返回 UNKNOWN。"""
        mock_ecs_instance_client._resolve_instance_state.return_value = "InvalidState"
        state = ecs_instance.get_state()
        assert state == EcsInstanceState.UNKNOWN

    def test_start_instance_success(self, ecs_instance, mock_ecs_instance_client):
        """测试启动实例（成功）。"""
        mock_ecs_instance_client.get_instance_id.return_value = "i-test123"
        ecs_instance._start_instance(wait=True)
        # 验证启动方法被调用
        mock_ecs_instance_client._client.start_instance_with_options.assert_called_once()
        # 验证等待方法被调用
        mock_ecs_instance_client.wait_instance.assert_called()

    def test_start_instance_failure(self, ecs_instance, mock_ecs_instance_client):
        """测试启动实例（失败）。"""
        mock_ecs_instance_client.get_instance_id.return_value = "i-test123"
        mock_ecs_instance_client._client.start_instance_with_options.side_effect = Exception("Start failed")
        with pytest.raises(RuntimeError, match="Fail to start instance"):
            ecs_instance._start_instance()

    def test_stop_instance_success(self, ecs_instance, mock_ecs_instance_client):
        """测试停止实例（成功）。"""
        ecs_instance._stop_instance()
        mock_ecs_instance_client.stop_instance.assert_called_once_with(wait=True)
        mock_ecs_instance_client.wait_instance.assert_called()

    def test_stop_instance_failure(self, ecs_instance, mock_ecs_instance_client):
        """测试停止实例（失败）。"""
        mock_ecs_instance_client.stop_instance.side_effect = Exception("Stop failed")
        with pytest.raises(RuntimeError, match="Fail to stop instance"):
            ecs_instance._stop_instance()

    def test_wait_for_start(self, ecs_instance, mock_ecs_instance_client):
        """测试等待实例启动。"""
        ecs_instance._wait_for_start()
        mock_ecs_instance_client.wait_instance.assert_called_with(state=BaseInstanceState.RUNNING.value)

    def test_wait_for_stop(self, ecs_instance, mock_ecs_instance_client):
        """测试等待实例停止。"""
        ecs_instance._wait_for_stop()
        mock_ecs_instance_client.wait_instance.assert_called_with(state=BaseInstanceState.STOPPED.value)

    def test_load_specification(self, ecs_instance, mock_ecs_instance_client):
        """测试加载实例规格。"""
        spec = ecs_instance._load_specification()
        assert isinstance(spec, dict)
        assert "InstanceId" in spec

    def test_run_command_with_wait(self, ecs_instance, mock_ecs_instance_client):
        """测试执行命令（等待完成）。"""
        result = ecs_instance.run_command(command="echo test", timeout=300, wait=True)

        # 验证命令启动
        mock_ecs_instance_client._start_command.assert_called_once_with(command="echo test", timeout=300)

        # 验证等待命令完成
        mock_ecs_instance_client._wait_command.assert_called_once()

        # 验证获取结果
        mock_ecs_instance_client._get_command_result.assert_called_once()

        # 验证返回结果
        assert isinstance(result, dict)

    def test_run_command_without_wait(self, ecs_instance, mock_ecs_instance_client):
        """测试执行命令（不等待完成）。"""
        result = ecs_instance.run_command(command="echo test", timeout=300, wait=False)

        # 验证命令启动
        mock_ecs_instance_client._start_command.assert_called_once()

        # 验证不等待命令完成
        mock_ecs_instance_client._wait_command.assert_not_called()

        # 验证不获取结果
        mock_ecs_instance_client._get_command_result.assert_not_called()

        # 验证返回包含 CommandId 和 InvokeId
        assert "CommandId" in result
        assert "InvokeId" in result

    def test_instance_inherits_from_base_instance(self, ecs_instance):
        """测试 EcsInstance 继承自 BaseInstance。"""
        from app.portal.instance.base.base import BaseInstance

        assert isinstance(ecs_instance, BaseInstance)

    def test_export_functionality(self, ecs_instance):
        """测试导出功能（继承自 BaseInstance）。"""
        ecs_instance.state = EcsInstanceState.RUNNING
        ecs_instance.spec = {"Cpu": 2, "Memory": 4096}

        exported = ecs_instance.export()

        assert exported["name"] == "test-ecs-instance"
        assert exported["host"] == "192.168.1.100"
        assert exported["port"] == 22
        assert exported["state"] == "running"
        assert exported["is_running"] is True
        assert "spec" in exported
