"""
综合测试：app.bridges.core.pipenode.state

覆盖范围
--------
- TestPipeNodeStatus    枚举值检查
- TestPipeNodeState     状态转换、属性计算
- TestStateTransition   start/finish/fail/cancel 状态转换
- TestExport            export() 和 describe() 方法
"""

from __future__ import annotations

import json
from datetime import datetime

from app.bridges.core.pipenode.state import PipeNodeState, PipeNodeStatus

# ──────────────────────────────────────────────────────────────────────────────
# TestPipeNodeStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestPipeNodeStatus:
    def test_status_enum_has_pending(self):
        """测试状态枚举包含 PENDING。"""
        assert hasattr(PipeNodeStatus, "PENDING")
        assert PipeNodeStatus.PENDING.value == "PENDING"

    def test_status_enum_has_running(self):
        """测试状态枚举包含 RUNNING。"""
        assert hasattr(PipeNodeStatus, "RUNNING")
        assert PipeNodeStatus.RUNNING.value == "RUNNING"

    def test_status_enum_has_success(self):
        """测试状态枚举包含 DONE。"""
        assert hasattr(PipeNodeStatus, "DONE")
        assert PipeNodeStatus.DONE.value == "DONE"

    def test_status_enum_has_failed(self):
        """测试状态枚举包含 FAILED。"""
        assert hasattr(PipeNodeStatus, "FAILED")
        assert PipeNodeStatus.FAILED.value == "FAILED"

    def test_status_enum_has_canceled(self):
        """测试状态枚举包含 CANCELED。"""
        assert hasattr(PipeNodeStatus, "CANCELED")
        assert PipeNodeStatus.CANCELED.value == "CANCELED"


# ──────────────────────────────────────────────────────────────────────────────
# TestPipeNodeState
# ──────────────────────────────────────────────────────────────────────────────


class TestPipeNodeState:
    def test_initial_status_is_pending(self):
        """测试初始状态为 PENDING。"""
        state = PipeNodeState()
        assert state.status == PipeNodeStatus.PENDING

    def test_initial_timestamps_are_none(self):
        """测试初始时间戳为 None。"""
        state = PipeNodeState()
        assert state.started_at is None
        assert state.finished_at is None

    def test_initial_rows_is_zero(self):
        """测试初始行数为 0。"""
        state = PipeNodeState()
        assert state.rows == 0

    def test_initial_error_is_none(self):
        """测试初始错误为 None。"""
        state = PipeNodeState()
        assert state.error is None

    def test_duration_is_none_when_not_finished(self):
        """测试未完成时 duration 为 None。"""
        state = PipeNodeState()
        assert state.duration_seconds is None

    def test_succeeded_is_false_initially(self):
        """测试初始时 succeeded 为 False。"""
        state = PipeNodeState()
        assert state.succeeded is False


# ──────────────────────────────────────────────────────────────────────────────
# TestStateTransition
# ──────────────────────────────────────────────────────────────────────────────


class TestStateTransition:
    def test_start_sets_status_to_running(self):
        """测试 start() 将状态设置为 RUNNING。"""
        state = PipeNodeState()
        state.start()
        assert state.status == PipeNodeStatus.RUNNING

    def test_start_sets_started_at(self):
        """测试 start() 设置 started_at。"""
        state = PipeNodeState()
        state.start()
        assert state.started_at is not None
        assert isinstance(state.started_at, datetime)

    def test_finish_sets_status_to_success(self):
        """测试 finish() 将状态设置为 DONE。"""
        state = PipeNodeState()
        state.start()
        state.finish(rows=100)
        assert state.status == PipeNodeStatus.DONE

    def test_finish_sets_finished_at(self):
        """测试 finish() 设置 finished_at。"""
        state = PipeNodeState()
        state.start()
        state.finish(rows=100)
        assert state.finished_at is not None
        assert isinstance(state.finished_at, datetime)

    def test_finish_sets_rows(self):
        """测试 finish() 设置 rows。"""
        state = PipeNodeState()
        state.start()
        state.finish(rows=100)
        assert state.rows == 100

    def test_finish_calculates_duration(self):
        """测试 finish() 后可以计算 duration。"""
        state = PipeNodeState()
        state.start()
        state.finish(rows=100)
        assert state.duration_seconds is not None
        assert state.duration_seconds >= 0

    def test_finish_sets_succeeded_to_true(self):
        """测试 finish() 后 succeeded 为 True。"""
        state = PipeNodeState()
        state.start()
        state.finish(rows=100)
        assert state.succeeded is True

    def test_fail_sets_status_to_failed(self):
        """测试 fail() 将状态设置为 FAILED。"""
        state = PipeNodeState()
        state.start()
        state.fail(error="Test error")
        assert state.status == PipeNodeStatus.FAILED

    def test_fail_sets_finished_at(self):
        """测试 fail() 设置 finished_at。"""
        state = PipeNodeState()
        state.start()
        state.fail(error="Test error")
        assert state.finished_at is not None

    def test_fail_sets_error_message(self):
        """测试 fail() 设置错误消息。"""
        state = PipeNodeState()
        state.start()
        state.fail(error="Test error")
        assert state.error == "Test error"

    def test_fail_sets_succeeded_to_false(self):
        """测试 fail() 后 succeeded 为 False。"""
        state = PipeNodeState()
        state.start()
        state.fail(error="Test error")
        assert state.succeeded is False

    def test_cancel_sets_status_to_canceled(self):
        """测试 cancel() 将状态设置为 CANCELED。"""
        state = PipeNodeState()
        state.start()
        state.cancel()
        assert state.status == PipeNodeStatus.CANCELED

    def test_cancel_sets_finished_at(self):
        """测试 cancel() 设置 finished_at。"""
        state = PipeNodeState()
        state.start()
        state.cancel()
        assert state.finished_at is not None


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        state = PipeNodeState()
        result = state.export()
        assert isinstance(result, dict)

    def test_export_contains_status(self):
        """测试 export() 包含 status。"""
        state = PipeNodeState()
        result = state.export()
        assert "status" in result
        assert result["status"] == PipeNodeStatus.PENDING.value

    def test_export_contains_timestamps(self):
        """测试 export() 包含时间戳。"""
        state = PipeNodeState()
        state.start()
        state.finish(rows=100)
        result = state.export()
        assert "started_at" in result
        assert "finished_at" in result

    def test_export_contains_rows(self):
        """测试 export() 包含 rows。"""
        state = PipeNodeState()
        state.start()
        state.finish(rows=100)
        result = state.export()
        assert "rows" in result
        assert result["rows"] == 100

    def test_export_contains_error_when_failed(self):
        """测试 export() 在失败时包含 error。"""
        state = PipeNodeState()
        state.start()
        state.fail(error="Test error")
        result = state.export()
        assert "error" in result
        assert result["error"] == "Test error"

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        state = PipeNodeState()
        result = state.describe()
        assert isinstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_export_contains_duration(self):
        """测试 export() 包含 duration_seconds。"""
        state = PipeNodeState()
        result = state.export()
        assert "duration_seconds" in result

    def test_describe_is_valid_json(self):
        """测试 describe() 返回有效 JSON。"""
        state = PipeNodeState()
        result = state.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_matches_export(self):
        """测试 describe() 内容与 export() 一致。"""
        state = PipeNodeState()
        state.start()
        state.finish(rows=100)
        export_data = state.export()
        describe_data = json.loads(state.describe())
        assert export_data == describe_data
