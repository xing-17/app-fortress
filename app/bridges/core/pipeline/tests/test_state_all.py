"""
综合测试：app.bridges.core.pipeline.state

覆盖范围
--------
- TestPipelineStatus    枚举值检查
- TestPipelineState     状态转换、属性计算
- TestStateTransition   start/finish/cancel 状态转换
- TestStateUpdate       update() 方法和节点统计
- TestExport            export() 和 describe() 方法
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import Mock

from app.bridges.core.pipeline.state import PipelineState, PipelineStatus
from app.bridges.core.pipenode.state import PipeNodeState, PipeNodeStatus

# ──────────────────────────────────────────────────────────────────────────────
# TestPipelineStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineStatus:
    def test_status_enum_has_pending(self):
        """测试状态枚举包含 PENDING。"""
        assert hasattr(PipelineStatus, "PENDING")
        assert PipelineStatus.PENDING.value == "PENDING"

    def test_status_enum_has_running(self):
        """测试状态枚举包含 RUNNING。"""
        assert hasattr(PipelineStatus, "RUNNING")
        assert PipelineStatus.RUNNING.value == "RUNNING"

    def test_status_enum_has_done(self):
        """测试状态枚举包含 DONE。"""
        assert hasattr(PipelineStatus, "DONE")
        assert PipelineStatus.DONE.value == "DONE"

    def test_status_enum_has_partial(self):
        """测试状态枚举包含 PARTIAL。"""
        assert hasattr(PipelineStatus, "PARTIAL")
        assert PipelineStatus.PARTIAL.value == "PARTIAL"

    def test_status_enum_has_failed(self):
        """测试状态枚举包含 FAILED。"""
        assert hasattr(PipelineStatus, "FAILED")
        assert PipelineStatus.FAILED.value == "FAILED"

    def test_status_enum_has_canceled(self):
        """测试状态枚举包含 CANCELED。"""
        assert hasattr(PipelineStatus, "CANCELED")
        assert PipelineStatus.CANCELED.value == "CANCELED"


# ──────────────────────────────────────────────────────────────────────────────
# TestPipelineState
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineState:
    def test_initial_status_is_pending(self):
        """测试初始状态为 PENDING。"""
        state = PipelineState()
        assert state.status == PipelineStatus.PENDING

    def test_initial_timestamps_are_none(self):
        """测试初始时间戳为 None。"""
        state = PipelineState()
        assert state.started_at is None
        assert state.finished_at is None

    def test_initial_counts_are_zero(self):
        """测试初始计数为 0。"""
        state = PipelineState()
        assert state.total == 0
        assert state.done == 0
        assert state.failed == 0
        assert state.running == 0
        assert state.pending == 0
        assert state.canceled == 0

    def test_duration_is_none_when_not_finished(self):
        """测试未完成时 duration 为 None。"""
        state = PipelineState()
        assert state.duration_seconds is None

    def test_succeeded_is_false_initially(self):
        """测试初始时 succeeded 为 False。"""
        state = PipelineState()
        assert state.succeeded is False


# ──────────────────────────────────────────────────────────────────────────────
# TestStateTransition
# ──────────────────────────────────────────────────────────────────────────────


class TestStateTransition:
    def test_start_sets_status_to_running(self):
        """测试 start() 将状态设置为 RUNNING。"""
        state = PipelineState()
        state.start()
        assert state.status == PipelineStatus.RUNNING

    def test_start_sets_started_at(self):
        """测试 start() 设置 started_at。"""
        state = PipelineState()
        state.start()
        assert state.started_at is not None
        assert isinstance(state.started_at, datetime)

    def test_cancel_sets_status_to_canceled(self):
        """测试 cancel() 将状态设置为 CANCELED。"""
        state = PipelineState()
        state.start()
        state.cancel()
        assert state.status == PipelineStatus.CANCELED

    def test_cancel_sets_finished_at(self):
        """测试 cancel() 设置 finished_at。"""
        state = PipelineState()
        state.start()
        state.cancel()
        assert state.finished_at is not None


# ──────────────────────────────────────────────────────────────────────────────
# TestStateUpdate
# ──────────────────────────────────────────────────────────────────────────────


def _create_mock_pipenode(status: PipeNodeStatus):
    """创建具有指定状态的 mock PipeNode"""
    node = Mock()
    node.state = PipeNodeState()
    node.state.status = status
    return node


class TestStateUpdate:
    def test_update_counts_total(self):
        """测试 update() 统计总数。"""
        state = PipelineState()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.DONE),
            _create_mock_pipenode(PipeNodeStatus.DONE),
            _create_mock_pipenode(PipeNodeStatus.FAILED),
        ]
        state.update(nodes)
        assert state.total == 3

    def test_update_counts_done(self):
        """测试 update() 统计成功数。"""
        state = PipelineState()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.DONE),
            _create_mock_pipenode(PipeNodeStatus.DONE),
            _create_mock_pipenode(PipeNodeStatus.FAILED),
        ]
        state.update(nodes)
        assert state.done == 2

    def test_update_counts_failed(self):
        """测试 update() 统计失败数。"""
        state = PipelineState()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.DONE),
            _create_mock_pipenode(PipeNodeStatus.FAILED),
            _create_mock_pipenode(PipeNodeStatus.FAILED),
        ]
        state.update(nodes)
        assert state.failed == 2

    def test_update_counts_running(self):
        """测试 update() 统计运行中数。"""
        state = PipelineState()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.RUNNING),
            _create_mock_pipenode(PipeNodeStatus.DONE),
        ]
        state.update(nodes)
        assert state.running == 1

    def test_update_counts_pending(self):
        """测试 update() 统计待运行数。"""
        state = PipelineState()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.PENDING),
            _create_mock_pipenode(PipeNodeStatus.PENDING),
            _create_mock_pipenode(PipeNodeStatus.DONE),
        ]
        state.update(nodes)
        assert state.pending == 2

    def test_update_counts_canceled(self):
        """测试 update() 统计已取消数。"""
        state = PipelineState()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.CANCELED),
            _create_mock_pipenode(PipeNodeStatus.DONE),
        ]
        state.update(nodes)
        assert state.canceled == 1

    def test_update_with_empty_nodes(self):
        """测试 update() 处理空节点列表。"""
        state = PipelineState()
        state.update([])
        assert state.total == 0
        assert state.done == 0
        assert state.failed == 0


# ──────────────────────────────────────────────────────────────────────────────
# TestFinish
# ──────────────────────────────────────────────────────────────────────────────


class TestFinish:
    def test_finish_sets_status_to_done_when_all_success(self):
        """测试 finish() 在全部成功时设置状态为 DONE。"""
        state = PipelineState()
        state.start()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.DONE),
            _create_mock_pipenode(PipeNodeStatus.DONE),
        ]
        state.finish(nodes)
        assert state.status == PipelineStatus.DONE

    def test_finish_sets_status_to_partial_when_mixed(self):
        """测试 finish() 在部分成功时设置状态为 PARTIAL。"""
        state = PipelineState()
        state.start()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.DONE),
            _create_mock_pipenode(PipeNodeStatus.FAILED),
        ]
        state.finish(nodes)
        assert state.status == PipelineStatus.PARTIAL

    def test_finish_sets_status_to_failed_when_all_failed(self):
        """测试 finish() 在全部失败时设置状态为 FAILED。"""
        state = PipelineState()
        state.start()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.FAILED),
            _create_mock_pipenode(PipeNodeStatus.FAILED),
        ]
        state.finish(nodes)
        assert state.status == PipelineStatus.FAILED

    def test_finish_sets_status_to_canceled_when_all_canceled(self):
        """测试 finish() 在全部取消时设置状态为 CANCELED。"""
        state = PipelineState()
        state.start()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.CANCELED),
            _create_mock_pipenode(PipeNodeStatus.CANCELED),
        ]
        state.finish(nodes)
        assert state.status == PipelineStatus.CANCELED

    def test_finish_sets_status_to_done_when_no_nodes(self):
        """测试 finish() 在无节点时设置状态为 DONE。"""
        state = PipelineState()
        state.start()
        state.finish([])
        assert state.status == PipelineStatus.DONE

    def test_finish_sets_finished_at(self):
        """测试 finish() 设置 finished_at。"""
        state = PipelineState()
        state.start()
        nodes = [_create_mock_pipenode(PipeNodeStatus.DONE)]
        state.finish(nodes)
        assert state.finished_at is not None

    def test_finish_updates_counts(self):
        """测试 finish() 更新计数。"""
        state = PipelineState()
        state.start()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.DONE),
            _create_mock_pipenode(PipeNodeStatus.FAILED),
        ]
        state.finish(nodes)
        assert state.total == 2
        assert state.done == 1
        assert state.failed == 1

    def test_finish_calculates_duration(self):
        """测试 finish() 后可以计算 duration。"""
        state = PipelineState()
        state.start()
        nodes = [_create_mock_pipenode(PipeNodeStatus.DONE)]
        state.finish(nodes)
        assert state.duration_seconds is not None
        assert state.duration_seconds >= 0

    def test_finish_sets_succeeded_to_true_when_done(self):
        """测试 finish() 在 DONE 状态时 succeeded 为 True。"""
        state = PipelineState()
        state.start()
        nodes = [_create_mock_pipenode(PipeNodeStatus.DONE)]
        state.finish(nodes)
        assert state.succeeded is True

    def test_finish_sets_succeeded_to_false_when_failed(self):
        """测试 finish() 在 FAILED 状态时 succeeded 为 False。"""
        state = PipelineState()
        state.start()
        nodes = [_create_mock_pipenode(PipeNodeStatus.FAILED)]
        state.finish(nodes)
        assert state.succeeded is False


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        state = PipelineState()
        result = state.export()
        assert isinstance(result, dict)

    def test_export_contains_status(self):
        """测试 export() 包含 status。"""
        state = PipelineState()
        result = state.export()
        assert "status" in result
        assert result["status"] == PipelineStatus.PENDING.value

    def test_export_contains_timestamps(self):
        """测试 export() 包含时间戳。"""
        state = PipelineState()
        state.start()
        nodes = [_create_mock_pipenode(PipeNodeStatus.DONE)]
        state.finish(nodes)
        result = state.export()
        assert "started_at" in result
        assert "finished_at" in result

    def test_export_contains_counts(self):
        """测试 export() 包含计数。"""
        state = PipelineState()
        state.start()
        nodes = [
            _create_mock_pipenode(PipeNodeStatus.DONE),
            _create_mock_pipenode(PipeNodeStatus.FAILED),
        ]
        state.finish(nodes)
        result = state.export()
        assert "total" in result
        assert "done" in result
        assert "failed" in result
        assert "running" in result
        assert "pending" in result
        assert "canceled" in result

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        state = PipelineState()
        result = state.describe()
        assert isinstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_is_valid_json(self):
        """测试 describe() 返回有效 JSON。"""
        state = PipelineState()
        result = state.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_matches_export(self):
        """测试 describe() 内容与 export() 一致。"""
        state = PipelineState()
        state.start()
        nodes = [_create_mock_pipenode(PipeNodeStatus.DONE)]
        state.finish(nodes)
        export_data = state.export()
        describe_data = json.loads(state.describe())
        assert export_data == describe_data
