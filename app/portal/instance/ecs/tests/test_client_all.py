"""
综合测试：app.portal.instance.ecs.client

覆盖范围
--------
- Test_EcsClient           客户端基础方法；实例信息获取；状态解析；命令执行流程
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.common.setting.portal import EcsInstanceSetting
from app.portal.instance.ecs.client import _EcsClient

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
def mock_ecs_client():
    """Mock 的 ECS Client fixture。"""
    with patch("app.portal.instance.ecs.client.EcsClient") as mock_client:
        # 设置默认的返回值
        mock_instance = MagicMock()
        mock_instance.describe_instances_with_options.return_value.body.instances.instance = [
            Mock(
                to_map=lambda: {
                    "InstanceId": "i-test123456",
                    "InstanceName": "test-ecs-instance",
                    "Status": "Running",
                    "Cpu": 2,
                    "Memory": 4096,
                }
            )
        ]
        mock_client.return_value = mock_instance
        yield mock_client


@pytest.fixture
def ecs_client(ecs_setting, mock_ecs_client):
    """_EcsClient 实例 fixture。"""
    return _EcsClient(
        instance_name=ecs_setting.name,
        region_id=ecs_setting.region,
        access_key_id=ecs_setting.access_key_id,
        access_key_secret=ecs_setting.access_key_secret,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test_EcsClient
# ──────────────────────────────────────────────────────────────────────────────


class Test_EcsClient:
    """测试 _EcsClient 类。"""

    def test_client_initialization(self, ecs_client, ecs_setting):
        """测试客户端初始化。"""
        assert ecs_client.instance_name == ecs_setting.name
        assert ecs_client.region_id == ecs_setting.region

    def test_get_instance_returns_instance_info(self, ecs_client):
        """测试获取实例信息。"""
        instance_info = ecs_client.get_instance()
        assert isinstance(instance_info, dict)
        assert "InstanceId" in instance_info
        assert instance_info["InstanceName"] == "test-ecs-instance"
        assert instance_info["Status"] == "Running"

    def test_resolve_instance_state(self, ecs_client):
        """测试状态解析。"""
        state = ecs_client._resolve_instance_state(payload={"Status": "Running", "InstanceId": "i-test"})
        assert state == "Running"

    def test_resolve_instance_state_without_payload(self, ecs_client):
        """测试无 payload 时的状态解析（需要调用 get_instance）。"""
        state = ecs_client._resolve_instance_state()
        assert state == "Running"

    def test_resolve_instance_id(self, ecs_client):
        """测试实例 ID 解析。"""
        instance_id = ecs_client._resolve_instance_id(payload={"InstanceId": "i-test123456", "Status": "Running"})
        assert instance_id == "i-test123456"

    def test_get_instance_id(self, ecs_client):
        """测试获取实例 ID。"""
        instance_id = ecs_client.get_instance_id()
        assert instance_id == "i-test123456"

    def test_get_instance_state(self, ecs_client):
        """测试获取实例状态。"""
        state = ecs_client.get_instance_state()
        assert state == "Running"

    def test_wait_instance_success(self, ecs_client):
        """测试等待实例到达指定状态（成功）。"""
        # wait_instance 应该正常返回而不抛出异常
        ecs_client.wait_instance(state="Running", timeout=10, interval=1)

    def test_start_command_returns_command_info(self, ecs_client):
        """测试启动命令执行。"""
        with patch.object(ecs_client._client, "run_command_with_options") as mock_run:
            mock_response = Mock()
            mock_response.body.to_map.return_value = {
                "CommandId": "c-test123",
                "InvokeId": "i-test123",
            }
            mock_run.return_value = mock_response

            result = ecs_client._start_command(command="echo test", timeout=300)
            assert result["CommandId"] == "c-test123"
            assert result["InvokeId"] == "i-test123"

    def test_get_command_result(self, ecs_client):
        """测试获取命令执行结果。"""
        with patch.object(ecs_client._client, "describe_invocation_results_with_options") as mock_describe:
            mock_response = Mock()
            mock_response.body.to_map.return_value = {
                "Invocation": {
                    "InvocationResults": {
                        "InvocationResult": [{"InvokeRecordStatus": "Finished", "Output": "dGVzdA=="}]
                    }
                }
            }
            mock_describe.return_value = mock_response

            result = ecs_client._get_command_result(command_id="c-test", invoke_id="i-test")
            assert "Invocation" in result

    def test_check_command_finished_true(self, ecs_client):
        """测试检查命令是否完成（已完成）。"""
        with patch.object(ecs_client, "_get_command_result") as mock_get:
            mock_get.return_value = {
                "Invocation": {"InvocationResults": {"InvocationResult": [{"InvokeRecordStatus": "Finished"}]}}
            }
            result = ecs_client._check_command_finished(command_id="c-test", invoke_id="i-test")
            assert result is True

    def test_check_command_finished_false(self, ecs_client):
        """测试检查命令是否完成（未完成）。"""
        with patch.object(ecs_client, "_get_command_result") as mock_get:
            mock_get.return_value = {
                "Invocation": {"InvocationResults": {"InvocationResult": [{"InvokeRecordStatus": "Running"}]}}
            }
            result = ecs_client._check_command_finished(command_id="c-test", invoke_id="i-test")
            assert result is False
