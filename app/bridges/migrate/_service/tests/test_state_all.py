"""
综合测试：app.bridges.migrate._service.state

覆盖范围
--------
- TestMigrateRequestStatus  枚举值检查
- TestMigrateRequestState   初始状态、属性
- TestStateTransition       start/finish/fail/cancel 状态转换
- TestProperties            succeeded/finished/total_rows 属性
- TestExport                export() 和 describe() 方法
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import Mock

from app.bridges.migrate._service.request import MigrateRequest
from app.bridges.migrate._service.state import MigrateRequestState, MigrateRequestStatus

# ──────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────────────────────


def _make_request() -> MigrateRequest:
    """创建测试用 MigrateRequest。"""
    return MigrateRequest(
        source_name="test_source",
        from_destination="oss_source",
        from_glob="s3://bucket/from/**/*.parquet",
        to_destination="oss_target",
    )


def _create_mock_node(rows: int = 0):
    """创建具有指定行数的 mock MigrateNode。"""
    node = Mock()
    node.state = Mock()
    node.state.rows = rows
    node.export = Mock(return_value={"node_id": "test_node"})
    return node


# ──────────────────────────────────────────────────────────────────────────────
# TestMigrateRequestStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestMigrateRequestStatus:
    def test_status_enum_has_pending(self):
        """测试状态枚举包含 PENDING。"""
        assert hasattr(MigrateRequestStatus, "PENDING")
        assert MigrateRequestStatus.PENDING.value == "PENDING"

    def test_status_enum_has_running(self):
        """测试状态枚举包含 RUNNING。"""
        assert hasattr(MigrateRequestStatus, "RUNNING")
        assert MigrateRequestStatus.RUNNING.value == "RUNNING"

    def test_status_enum_has_done(self):
        """测试状态枚举包含 DONE。"""
        assert hasattr(MigrateRequestStatus, "DONE")
        assert MigrateRequestStatus.DONE.value == "DONE"

    def test_status_enum_has_partial(self):
        """测试状态枚举包含 PARTIAL。"""
        assert hasattr(MigrateRequestStatus, "PARTIAL")
        assert MigrateRequestStatus.PARTIAL.value == "PARTIAL"

    def test_status_enum_has_failed(self):
        """测试状态枚举包含 FAILED。"""
        assert hasattr(MigrateRequestStatus, "FAILED")
        assert MigrateRequestStatus.FAILED.value == "FAILED"

    def test_status_enum_has_canceled(self):
        """测试状态枚举包含 CANCELED。"""
        assert hasattr(MigrateRequestStatus, "CANCELED")
        assert MigrateRequestStatus.CANCELED.value == "CANCELED"


# ──────────────────────────────────────────────────────────────────────────────
# TestMigrateRequestState
# ──────────────────────────────────────────────────────────────────────────────


class TestMigrateRequestState:
    def test_initial_status_is_pending(self):
        """测试初始状态为 PENDING。"""
        state = MigrateRequestState(request=_make_request())
        assert state.status == MigrateRequestStatus.PENDING

    def test_initial_timestamps_are_none(self):
        """测试初始时间戳为 None。"""
        state = MigrateRequestState(request=_make_request())
        assert state.started_at is None
        assert state.finished_at is None

    def test_initial_node_is_none(self):
        """测试初始 node 为 None。"""
        state = MigrateRequestState(request=_make_request())
        assert state.node is None

    def test_initial_error_is_none(self):
        """测试初始 error 为 None。"""
        state = MigrateRequestState(request=_make_request())
        assert state.error is None

    def test_succeeded_is_false_initially(self):
        """测试初始时 succeeded 为 False。"""
        state = MigrateRequestState(request=_make_request())
        assert state.succeeded is False

    def test_finished_is_false_initially(self):
        """测试初始时 finished 为 False。"""
        state = MigrateRequestState(request=_make_request())
        assert state.finished is False

    def test_duration_is_none_when_not_finished(self):
        """测试未完成时 duration_seconds 为 None。"""
        state = MigrateRequestState(request=_make_request())
        assert state.duration_seconds is None

    def test_total_rows_is_zero_initially(self):
        """测试初始时 total_rows 为 0。"""
        state = MigrateRequestState(request=_make_request())
        assert state.total_rows == 0

    def test_request_is_accessible(self):
        """测试 request 可访问。"""
        req = _make_request()
        state = MigrateRequestState(request=req)
        assert state.request == req


# ──────────────────────────────────────────────────────────────────────────────
# TestStateTransition
# ──────────────────────────────────────────────────────────────────────────────


class TestStateTransition:
    def test_start_sets_status_to_running(self):
        """测试 start() 将状态设置为 RUNNING。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        assert state.status == MigrateRequestStatus.RUNNING

    def test_start_sets_started_at(self):
        """测试 start() 设置 started_at。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        assert state.started_at is not None
        assert isinstance(state.started_at, datetime)

    def test_finish_sets_status_to_done(self):
        """测试 finish() 将状态设置为 DONE。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.finish()
        assert state.status == MigrateRequestStatus.DONE

    def test_finish_sets_finished_at(self):
        """测试 finish() 设置 finished_at。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.finish()
        assert state.finished_at is not None
        assert isinstance(state.finished_at, datetime)

    def test_finish_calculates_duration(self):
        """测试 finish() 后可以计算 duration。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.finish()
        assert state.duration_seconds is not None
        assert state.duration_seconds >= 0

    def test_finish_sets_succeeded_to_true(self):
        """测试 finish() 后 succeeded 为 True。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.finish()
        assert state.succeeded is True

    def test_finish_sets_finished_to_true(self):
        """测试 finish() 后 finished 为 True。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.finish()
        assert state.finished is True

    def test_fail_sets_status_to_failed(self):
        """测试 fail() 将状态设置为 FAILED。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.fail(error="Test error")
        assert state.status == MigrateRequestStatus.FAILED

    def test_fail_sets_finished_at(self):
        """测试 fail() 设置 finished_at。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.fail(error="Test error")
        assert state.finished_at is not None

    def test_fail_sets_error_message(self):
        """测试 fail() 设置错误消息。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.fail(error="Test error")
        assert state.error == "Test error"

    def test_fail_sets_succeeded_to_false(self):
        """测试 fail() 后 succeeded 为 False。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.fail(error="Test error")
        assert state.succeeded is False

    def test_fail_sets_finished_to_true(self):
        """测试 fail() 后 finished 为 True。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.fail(error="Test error")
        assert state.finished is True

    def test_cancel_sets_status_to_canceled(self):
        """测试 cancel() 将状态设置为 CANCELED。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.cancel()
        assert state.status == MigrateRequestStatus.CANCELED

    def test_cancel_sets_finished_at(self):
        """测试 cancel() 设置 finished_at。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.cancel()
        assert state.finished_at is not None

    def test_cancel_sets_finished_to_true(self):
        """测试 cancel() 后 finished 为 True。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.cancel()
        assert state.finished is True


# ──────────────────────────────────────────────────────────────────────────────
# TestProperties
# ──────────────────────────────────────────────────────────────────────────────


class TestProperties:
    def test_total_rows_returns_zero_when_no_node(self):
        """测试没有 node 时 total_rows 返回 0。"""
        state = MigrateRequestState(request=_make_request())
        assert state.total_rows == 0

    def test_total_rows_returns_node_rows_when_node_exists(self):
        """测试有 node 时 total_rows 返回 node 的行数。"""
        state = MigrateRequestState(request=_make_request())
        state.node = _create_mock_node(rows=1000)
        assert state.total_rows == 1000

    def test_succeeded_is_true_when_status_is_done(self):
        """测试状态为 DONE 时 succeeded 为 True。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.finish()
        assert state.succeeded is True

    def test_succeeded_is_false_when_status_is_failed(self):
        """测试状态为 FAILED 时 succeeded 为 False。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.fail(error="Test error")
        assert state.succeeded is False

    def test_finished_is_true_for_done_status(self):
        """测试 DONE 状态时 finished 为 True。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.finish()
        assert state.finished is True

    def test_finished_is_true_for_failed_status(self):
        """测试 FAILED 状态时 finished 为 True。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.fail(error="Test error")
        assert state.finished is True

    def test_finished_is_true_for_canceled_status(self):
        """测试 CANCELED 状态时 finished 为 True。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.cancel()
        assert state.finished is True

    def test_finished_is_false_for_running_status(self):
        """测试 RUNNING 状态时 finished 为 False。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        assert state.finished is False


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        state = MigrateRequestState(request=_make_request())
        result = state.export()
        assert isinstance(result, dict)

    def test_export_contains_status(self):
        """测试 export() 包含 status。"""
        state = MigrateRequestState(request=_make_request())
        result = state.export()
        assert "status" in result
        assert result["status"] == MigrateRequestStatus.PENDING.value

    def test_export_contains_request(self):
        """测试 export() 包含 request。"""
        state = MigrateRequestState(request=_make_request())
        result = state.export()
        assert "request" in result
        assert isinstance(result["request"], dict)

    def test_export_contains_node_when_node_exists(self):
        """测试有 node 时 export() 包含 node。"""
        state = MigrateRequestState(request=_make_request())
        state.node = _create_mock_node()
        result = state.export()
        assert "node" in result
        assert result["node"] == {"node_id": "test_node"}

    def test_export_contains_node_none_when_no_node(self):
        """测试没有 node 时 export() 的 node 为 None。"""
        state = MigrateRequestState(request=_make_request())
        result = state.export()
        assert "node" in result
        assert result["node"] is None

    def test_export_contains_error(self):
        """测试 export() 包含 error。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.fail(error="Test error")
        result = state.export()
        assert "error" in result
        assert result["error"] == "Test error"

    def test_export_contains_error_none_when_not_failed(self):
        """测试未失败时 export() 的 error 为 None。"""
        state = MigrateRequestState(request=_make_request())
        result = state.export()
        assert "error" in result
        assert result["error"] is None

    def test_export_contains_timestamps(self):
        """测试 export() 包含时间戳。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.finish()
        result = state.export()
        assert "started_at" in result
        assert "finished_at" in result

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        state = MigrateRequestState(request=_make_request())
        result = state.describe()
        assert isinstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_export_contains_duration(self):
        """测试 export() 包含 duration_seconds。"""
        state = MigrateRequestState(request=_make_request())
        result = state.export()
        assert "duration_seconds" in result

    def test_describe_is_valid_json(self):
        """测试 describe() 返回有效 JSON。"""
        state = MigrateRequestState(request=_make_request())
        state.start()
        state.finish()
        result = state.describe()
        parsed = json.loads(result)
        assert "status" in parsed
        assert "request" in parsed
