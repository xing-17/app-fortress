"""
综合测试：bastion.domain.run.base

覆盖范围
--------
- TestRunStatus         枚举值正确性；from_any() 类型转换；无效值处理
- TestBaseRunModel      初始化；ID 生成；状态机转换；export() 序列化
- TestStateTransitions  状态转换合法性；非法转换检测；时间戳正确性
- TestExport            export() 返回格式；datetime 序列化；字段完整性
"""

from __future__ import annotations

from datetime import UTC

import pytest
from pydantic import ValidationError

from bastion.domain.run import (
    BaseRunModel,
    RunStatus,
)

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures & Helpers
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_run():
    """创建一个测试用的 Run 实例。"""
    return BaseRunModel(
        bridge_name="test_bridge",
    )


# ──────────────────────────────────────────────────────────────────────────────
# TestRunStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestRunStatus:
    """测试 RunStatus 枚举。"""

    def test_enum_values_exist(self):
        """测试所有状态值存在。"""
        assert RunStatus.PENDING == "pending"
        assert RunStatus.RUNNING == "running"
        assert RunStatus.SUCCEEDED == "succeeded"
        assert RunStatus.FAILED == "failed"
        assert RunStatus.CANCELLED == "cancelled"

    def test_from_any_accepts_string(self):
        """测试 from_any() 接受字符串。"""
        assert RunStatus.from_any("pending") == RunStatus.PENDING
        assert RunStatus.from_any("running") == RunStatus.RUNNING

    def test_from_any_accepts_enum(self):
        """测试 from_any() 接受枚举值。"""
        assert RunStatus.from_any(RunStatus.PENDING) == RunStatus.PENDING

    def test_from_any_invalid_value_raises(self):
        """测试 from_any() 对无效值抛出异常。"""
        with pytest.raises(ValueError, match="Invalid RunStatus value"):
            RunStatus.from_any("invalid_status")


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseRunModel
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseRunModel:
    """测试 BaseRunModel 基本功能。"""

    def test_init_with_required_fields(self):
        """测试使用必填字段初始化。"""
        run = BaseRunModel(bridge_name="test_bridge")
        assert run.bridge_name == "test_bridge"

    def test_init_auto_generates_id(self, sample_run):
        """测试自动生成 ID。"""
        assert sample_run.id.startswith("run-")
        assert len(sample_run.id) == 20  # "run-" (4) + 16 chars

    def test_init_default_status_is_pending(self, sample_run):
        """测试默认状态为 PENDING。"""
        assert sample_run.status == RunStatus.PENDING

    def test_init_sets_created_at(self, sample_run):
        """测试自动设置 created_at。"""
        assert sample_run.created_at is not None
        assert sample_run.created_at.tzinfo == UTC

    def test_init_started_at_is_none(self, sample_run):
        """测试 started_at 初始为 None。"""
        assert sample_run.started_at is None

    def test_init_finished_at_is_none(self, sample_run):
        """测试 finished_at 初始为 None。"""
        assert sample_run.finished_at is None

    def test_missing_bridge_name_raises(self):
        """测试缺少 bridge_name 时抛出异常。"""
        with pytest.raises(ValidationError):
            BaseRunModel()


# ──────────────────────────────────────────────────────────────────────────────
# TestStateTransitions
# ──────────────────────────────────────────────────────────────────────────────


class TestStateTransitions:
    """测试状态机转换。"""

    def test_start_changes_status_to_running(self, sample_run):
        """测试 start() 改变状态为 RUNNING。"""
        sample_run.start()
        assert sample_run.status == RunStatus.RUNNING

    def test_start_sets_started_at(self, sample_run):
        """测试 start() 设置 started_at。"""
        sample_run.start()
        assert sample_run.started_at is not None
        assert sample_run.started_at.tzinfo == UTC

    def test_succeed_changes_status_to_succeeded(self, sample_run):
        """测试 succeed() 改变状态为 SUCCEEDED。"""
        sample_run.start()
        sample_run.succeed()
        assert sample_run.status == RunStatus.SUCCEEDED

    def test_succeed_sets_finished_at(self, sample_run):
        """测试 succeed() 设置 finished_at。"""
        sample_run.start()
        sample_run.succeed()
        assert sample_run.finished_at is not None
        assert sample_run.finished_at.tzinfo == UTC

    def test_fail_changes_status_to_failed(self, sample_run):
        """测试 fail() 改变状态为 FAILED。"""
        sample_run.start()
        sample_run.fail()
        assert sample_run.status == RunStatus.FAILED

    def test_fail_sets_finished_at(self, sample_run):
        """测试 fail() 设置 finished_at。"""
        sample_run.start()
        sample_run.fail()
        assert sample_run.finished_at is not None

    def test_cancel_changes_status_to_cancelled(self, sample_run):
        """测试 cancel() 改变状态为 CANCELLED。"""
        sample_run.start()
        sample_run.cancel()
        assert sample_run.status == RunStatus.CANCELLED

    def test_cancel_sets_finished_at(self, sample_run):
        """测试 cancel() 设置 finished_at。"""
        sample_run.start()
        sample_run.cancel()
        assert sample_run.finished_at is not None

    def test_full_success_workflow(self, sample_run):
        """测试完整成功流程：PENDING → RUNNING → SUCCEEDED。"""
        assert sample_run.status == RunStatus.PENDING
        sample_run.start()
        assert sample_run.status == RunStatus.RUNNING
        sample_run.succeed()
        assert sample_run.status == RunStatus.SUCCEEDED

    def test_full_failure_workflow(self, sample_run):
        """测试完整失败流程：PENDING → RUNNING → FAILED。"""
        assert sample_run.status == RunStatus.PENDING
        sample_run.start()
        assert sample_run.status == RunStatus.RUNNING
        sample_run.fail()
        assert sample_run.status == RunStatus.FAILED

    # TODO: 添加非法状态转换测试
    # def test_start_from_succeeded_raises(self, sample_run):
    #     """测试从 SUCCEEDED 状态调用 start() 抛出异常。"""
    #     sample_run.start()
    #     sample_run.succeed()
    #     with pytest.raises(ValueError):
    #         sample_run.start()


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    """测试 export() 序列化。"""

    def test_export_returns_dict(self, sample_run):
        """测试 export() 返回字典。"""
        result = sample_run.export()
        assert isinstance(result, dict)

    def test_export_contains_all_keys(self, sample_run):
        """测试 export() 包含所有必需字段。"""
        result = sample_run.export()
        assert "id" in result
        assert "bridge_name" in result
        assert "status" in result
        assert "created_at" in result
        assert "started_at" in result
        assert "finished_at" in result

    def test_export_id_is_string(self, sample_run):
        """测试 export() 的 id 是字符串。"""
        result = sample_run.export()
        assert isinstance(result["id"], str)

    def test_export_status_is_string_value(self, sample_run):
        """测试 export() 的 status 是字符串值。"""
        result = sample_run.export()
        assert result["status"] == "pending"

    def test_export_datetime_is_iso_string_or_none(self, sample_run):
        """测试 export() 的 datetime 是 ISO 字符串或 None。"""
        result = sample_run.export()
        # created_at 应该是 ISO 字符串
        assert isinstance(result["created_at"], str)
        assert "T" in result["created_at"]
        # started_at 和 finished_at 应该是 None
        assert result["started_at"] is None
        assert result["finished_at"] is None

    def test_export_after_start_has_started_at(self, sample_run):
        """测试 start() 后 export() 包含 started_at。"""
        sample_run.start()
        result = sample_run.export()
        assert result["started_at"] is not None
        assert isinstance(result["started_at"], str)

    def test_export_after_succeed_has_finished_at(self, sample_run):
        """测试 succeed() 后 export() 包含 finished_at。"""
        sample_run.start()
        sample_run.succeed()
        result = sample_run.export()
        assert result["finished_at"] is not None
        assert isinstance(result["finished_at"], str)


# ──────────────────────────────────────────────────────────────────────────────
# TestEdgeCases
# ──────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """测试边界情况。"""

    def test_multiple_start_calls(self, sample_run):
        """测试多次调用 start()。

        TODO: 应该抛出异常，但当前实现允许。
        """
        sample_run.start()
        first_started_at = sample_run.started_at
        # 目前这会成功，但理想情况下应该抛出异常
        sample_run.start()
        assert sample_run.started_at != first_started_at  # 时间被更新了

    def test_succeed_without_start(self, sample_run):
        """测试在未 start() 的情况下调用 succeed()。

        TODO: 应该抛出异常，但当前实现允许。
        """
        # 目前这会成功，但理想情况下应该抛出异常
        sample_run.succeed()
        assert sample_run.status == RunStatus.SUCCEEDED
