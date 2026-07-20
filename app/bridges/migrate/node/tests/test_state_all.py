"""
综合测试：app.bridges.migrate.node.state

覆盖范围
--------
- TestMigrateNodeStatus    枚举值检查
- TestMigrateNodeState     状态转换、属性计算
- TestStateTransition      start/finish/fail/cancel 状态转换
- TestExport               export() 和 describe() 方法
"""

from __future__ import annotations

import json
from datetime import datetime

from app.bridges.migrate.node.state import MigrateNodeState, MigrateNodeStatus

# ──────────────────────────────────────────────────────────────────────────────
# TestMigrateNodeStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestMigrateNodeStatus:
    def test_status_enum_has_pending(self):
        """测试状态枚举包含 PENDING。"""
        assert hasattr(MigrateNodeStatus, "PENDING")
        assert MigrateNodeStatus.PENDING.value == "PENDING"

    def test_status_enum_has_running(self):
        """测试状态枚举包含 RUNNING。"""
        assert hasattr(MigrateNodeStatus, "RUNNING")
        assert MigrateNodeStatus.RUNNING.value == "RUNNING"

    def test_status_enum_has_done(self):
        """测试状态枚举包含 DONE。"""
        assert hasattr(MigrateNodeStatus, "DONE")
        assert MigrateNodeStatus.DONE.value == "DONE"

    def test_status_enum_has_failed(self):
        """测试状态枚举包含 FAILED。"""
        assert hasattr(MigrateNodeStatus, "FAILED")
        assert MigrateNodeStatus.FAILED.value == "FAILED"

    def test_status_enum_has_canceled(self):
        """测试状态枚举包含 CANCELED。"""
        assert hasattr(MigrateNodeStatus, "CANCELED")
        assert MigrateNodeStatus.CANCELED.value == "CANCELED"


# ──────────────────────────────────────────────────────────────────────────────
# TestMigrateNodeState
# ──────────────────────────────────────────────────────────────────────────────


class TestMigrateNodeState:
    def test_initial_status_is_pending(self):
        """测试初始状态为 PENDING。"""
        state = MigrateNodeState()
        assert state.status == MigrateNodeStatus.PENDING

    def test_initial_timestamps_are_none(self):
        """测试初始时间戳为 None。"""
        state = MigrateNodeState()
        assert state.started_at is None
        assert state.finished_at is None

    def test_initial_rows_is_zero(self):
        """测试初始行数为 0。"""
        state = MigrateNodeState()
        assert state.rows == 0

    def test_initial_error_is_none(self):
        """测试初始错误为 None。"""
        state = MigrateNodeState()
        assert state.error is None

    def test_duration_is_none_when_not_finished(self):
        """测试未完成时 duration 为 None。"""
        state = MigrateNodeState()
        assert state.duration_seconds is None

    def test_succeeded_is_false_initially(self):
        """测试初始时 succeeded 为 False。"""
        state = MigrateNodeState()
        assert state.succeeded is False

    def test_finished_is_false_initially(self):
        """测试初始时 finished 为 False。"""
        state = MigrateNodeState()
        assert state.finished is False

    def test_type_is_migrate_node(self):
        """测试 type 为 migrate_node。"""
        state = MigrateNodeState()
        assert state.type == "migrate_node"


# ──────────────────────────────────────────────────────────────────────────────
# TestStateTransition
# ──────────────────────────────────────────────────────────────────────────────


class TestStateTransition:
    def test_start_sets_status_to_running(self):
        """测试 start() 将状态设置为 RUNNING。"""
        state = MigrateNodeState()
        state.start()
        assert state.status == MigrateNodeStatus.RUNNING

    def test_start_sets_started_at(self):
        """测试 start() 设置 started_at。"""
        state = MigrateNodeState()
        state.start()
        assert state.started_at is not None
        assert isinstance(state.started_at, datetime)

    def test_finish_sets_status_to_done(self):
        """测试 finish() 将状态设置为 DONE。"""
        state = MigrateNodeState()
        state.start()
        state.finish(rows=100)
        assert state.status == MigrateNodeStatus.DONE

    def test_finish_sets_finished_at(self):
        """测试 finish() 设置 finished_at。"""
        state = MigrateNodeState()
        state.start()
        state.finish(rows=100)
        assert state.finished_at is not None
        assert isinstance(state.finished_at, datetime)

    def test_finish_sets_rows(self):
        """测试 finish() 设置 rows。"""
        state = MigrateNodeState()
        state.start()
        state.finish(rows=100)
        assert state.rows == 100

    def test_finish_calculates_duration(self):
        """测试 finish() 后可以计算 duration。"""
        state = MigrateNodeState()
        state.start()
        state.finish(rows=100)
        assert state.duration_seconds is not None
        assert state.duration_seconds >= 0

    def test_finish_sets_succeeded_to_true(self):
        """测试 finish() 后 succeeded 为 True。"""
        state = MigrateNodeState()
        state.start()
        state.finish(rows=100)
        assert state.succeeded is True

    def test_finish_sets_finished_to_true(self):
        """测试 finish() 后 finished 为 True。"""
        state = MigrateNodeState()
        state.start()
        state.finish(rows=100)
        assert state.finished is True

    def test_fail_sets_status_to_failed(self):
        """测试 fail() 将状态设置为 FAILED。"""
        state = MigrateNodeState()
        state.start()
        state.fail(error="Test error")
        assert state.status == MigrateNodeStatus.FAILED

    def test_fail_sets_finished_at(self):
        """测试 fail() 设置 finished_at。"""
        state = MigrateNodeState()
        state.start()
        state.fail(error="Test error")
        assert state.finished_at is not None

    def test_fail_sets_error_message(self):
        """测试 fail() 设置错误消息。"""
        state = MigrateNodeState()
        state.start()
        state.fail(error="Test error")
        assert state.error == "Test error"

    def test_fail_sets_succeeded_to_false(self):
        """测试 fail() 后 succeeded 为 False。"""
        state = MigrateNodeState()
        state.start()
        state.fail(error="Test error")
        assert state.succeeded is False

    def test_fail_sets_finished_to_true(self):
        """测试 fail() 后 finished 为 True。"""
        state = MigrateNodeState()
        state.start()
        state.fail(error="Test error")
        assert state.finished is True

    def test_cancel_sets_status_to_canceled(self):
        """测试 cancel() 将状态设置为 CANCELED。"""
        state = MigrateNodeState()
        state.start()
        state.cancel()
        assert state.status == MigrateNodeStatus.CANCELED

    def test_cancel_sets_finished_at(self):
        """测试 cancel() 设置 finished_at。"""
        state = MigrateNodeState()
        state.start()
        state.cancel()
        assert state.finished_at is not None

    def test_cancel_sets_finished_to_true(self):
        """测试 cancel() 后 finished 为 True。"""
        state = MigrateNodeState()
        state.start()
        state.cancel()
        assert state.finished is True


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        state = MigrateNodeState()
        result = state.export()
        assert isinstance(result, dict)

    def test_export_contains_status(self):
        """测试 export() 包含 status。"""
        state = MigrateNodeState()
        result = state.export()
        assert "status" in result
        assert result["status"] == MigrateNodeStatus.PENDING.value

    def test_export_contains_type(self):
        """测试 export() 包含 type。"""
        state = MigrateNodeState()
        result = state.export()
        assert "type" in result
        assert result["type"] == "migrate_node"

    def test_export_contains_timestamps(self):
        """测试 export() 包含时间戳。"""
        state = MigrateNodeState()
        state.start()
        state.finish(rows=100)
        result = state.export()
        assert "started_at" in result
        assert "finished_at" in result

    def test_export_contains_rows(self):
        """测试 export() 包含 rows。"""
        state = MigrateNodeState()
        state.start()
        state.finish(rows=100)
        result = state.export()
        assert "rows" in result
        assert result["rows"] == 100

    def test_export_contains_error_when_failed(self):
        """测试 export() 在失败时包含 error。"""
        state = MigrateNodeState()
        state.start()
        state.fail(error="Test error")
        result = state.export()
        assert "error" in result
        assert result["error"] == "Test error"

    def test_export_contains_error_none_when_not_failed(self):
        """测试 export() 在未失败时 error 为 None。"""
        state = MigrateNodeState()
        result = state.export()
        assert "error" in result
        assert result["error"] is None

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        state = MigrateNodeState()
        result = state.describe()
        assert isinstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_export_contains_duration(self):
        """测试 export() 包含 duration_seconds。"""
        state = MigrateNodeState()
        result = state.export()
        assert "duration_seconds" in result

    def test_describe_is_valid_json(self):
        """测试 describe() 返回有效 JSON。"""
        state = MigrateNodeState()
        state.start()
        state.finish(rows=100)
        result = state.describe()
        parsed = json.loads(result)
        assert "status" in parsed
        assert "rows" in parsed

    def test_export_contains_succeeded(self):
        """测试 export() 包含 succeeded。"""
        state = MigrateNodeState()
        result = state.export()
        assert "succeeded" in result
        assert result["succeeded"] is False

    def test_export_succeeded_is_true_when_done(self):
        """测试 export() 在 DONE 状态时 succeeded 为 True。"""
        state = MigrateNodeState()
        state.start()
        state.finish(rows=100)
        result = state.export()
        assert result["succeeded"] is True
