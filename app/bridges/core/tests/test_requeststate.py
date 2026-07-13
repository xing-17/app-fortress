"""
综合测试：app.bridges.core.requeststate

覆盖范围
--------
- TestBridgesRequestStatus   枚举值检查
- TestBridgesRequestState    状态转换、属性计算
- TestStateTransition        start/update/finish/cancel 状态转换
- TestExport                 export()、describe()、report() 方法
"""

from __future__ import annotations

import json
from unittest.mock import Mock

from app.bridges.core.request import BridgesRequest
from app.bridges.core.requeststate import BridgesRequestState, BridgesRequestStatus
from app.bridges.pipelines.state import PipeStatus

# ──────────────────────────────────────────────────────────────────────────────
# TestBridgesRequestStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgesRequestStatus:
    def test_status_enum_has_pending(self):
        """测试状态枚举包含 PENDING。"""
        assert hasattr(BridgesRequestStatus, "PENDING")
        assert BridgesRequestStatus.PENDING.value == "PENDING"

    def test_status_enum_has_running(self):
        """测试状态枚举包含 RUNNING。"""
        assert hasattr(BridgesRequestStatus, "RUNNING")
        assert BridgesRequestStatus.RUNNING.value == "RUNNING"

    def test_status_enum_has_done(self):
        """测试状态枚举包含 DONE。"""
        assert hasattr(BridgesRequestStatus, "DONE")
        assert BridgesRequestStatus.DONE.value == "DONE"

    def test_status_enum_has_partial(self):
        """测试状态枚举包含 PARTIAL。"""
        assert hasattr(BridgesRequestStatus, "PARTIAL")
        assert BridgesRequestStatus.PARTIAL.value == "PARTIAL"

    def test_status_enum_has_failed(self):
        """测试状态枚举包含 FAILED。"""
        assert hasattr(BridgesRequestStatus, "FAILED")
        assert BridgesRequestStatus.FAILED.value == "FAILED"

    def test_status_enum_has_canceled(self):
        """测试状态枚举包含 CANCELED。"""
        assert hasattr(BridgesRequestStatus, "CANCELED")
        assert BridgesRequestStatus.CANCELED.value == "CANCELED"


# ──────────────────────────────────────────────────────────────────────────────
# TestBridgesRequestState
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgesRequestState:
    def test_initial_status_is_pending(self):
        """测试初始状态为 PENDING。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        assert state.status == BridgesRequestStatus.PENDING

    def test_initial_timestamps_are_none(self):
        """测试初始时间戳为 None。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        assert state.started_at is None
        assert state.finished_at is None

    def test_initial_counters_are_zero(self):
        """测试初始计数器为 0。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        assert state.total == 0
        assert state.success == 0
        assert state.partial == 0
        assert state.failed == 0
        assert state.running == 0
        assert state.pending == 0
        assert state.canceled == 0

    def test_initial_pipe_nodes_is_empty(self):
        """测试初始 pipe_nodes 为空列表。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        assert state.pipe_nodes == []


# ──────────────────────────────────────────────────────────────────────────────
# TestStateTransition
# ──────────────────────────────────────────────────────────────────────────────


class TestStateTransition:
    def _create_mock_pipe_node(self, status: PipeStatus):
        """创建 mock PipeNode。"""
        mock_state = Mock()
        mock_state.status = status

        mock_node = Mock()
        mock_node.state = mock_state
        return mock_node

    def test_start_changes_status_to_running(self):
        """测试 start() 改变状态为 RUNNING。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)

        nodes = [self._create_mock_pipe_node(PipeStatus.PENDING)]
        state.start(nodes)

        assert state.status == BridgesRequestStatus.RUNNING
        assert state.started_at is not None

    def test_start_sets_total_and_pending(self):
        """测试 start() 设置 total 和 pending。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.PENDING),
            self._create_mock_pipe_node(PipeStatus.PENDING),
            self._create_mock_pipe_node(PipeStatus.PENDING),
        ]
        state.start(nodes)

        assert state.total == 3
        assert state.pending == 3

    def test_cancel_changes_status_to_canceled(self):
        """测试 cancel() 改变状态为 CANCELED。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)

        state.cancel()

        assert state.status == BridgesRequestStatus.CANCELED
        assert state.finished_at is not None

    def test_is_cancelled_returns_true_when_canceled(self):
        """测试 _is_cancelled() 在取消后返回 True。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)

        assert state._is_cancelled() is False
        state.cancel()
        assert state._is_cancelled() is True

    def test_update_counts_nodes_by_status(self):
        """测试 update() 按状态计数节点。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.DONE),
            self._create_mock_pipe_node(PipeStatus.DONE),
            self._create_mock_pipe_node(PipeStatus.PARTIAL),
            self._create_mock_pipe_node(PipeStatus.FAILED),
            self._create_mock_pipe_node(PipeStatus.RUNNING),
            self._create_mock_pipe_node(PipeStatus.PENDING),
        ]
        state.update(nodes)

        assert state.total == 6
        assert state.success == 2
        assert state.partial == 1
        assert state.failed == 1
        assert state.running == 1
        assert state.pending == 1

    def test_finish_with_all_success_sets_done(self):
        """测试 finish() 在全部成功时设置为 DONE。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.DONE),
            self._create_mock_pipe_node(PipeStatus.DONE),
        ]
        state.finish(nodes)

        assert state.status == BridgesRequestStatus.DONE
        assert state.finished_at is not None

    def test_finish_with_partial_and_success_sets_done(self):
        """测试 finish() 在部分成功+全部成功时设置为 DONE。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.DONE),
            self._create_mock_pipe_node(PipeStatus.PARTIAL),
        ]
        state.finish(nodes)

        assert state.status == BridgesRequestStatus.DONE

    def test_finish_with_success_and_failure_sets_partial(self):
        """测试 finish() 在成功+失败时设置为 PARTIAL。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.DONE),
            self._create_mock_pipe_node(PipeStatus.FAILED),
        ]
        state.finish(nodes)

        assert state.status == BridgesRequestStatus.PARTIAL

    def test_finish_with_all_failed_sets_failed(self):
        """测试 finish() 在全部失败时设置为 FAILED。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.FAILED),
            self._create_mock_pipe_node(PipeStatus.FAILED),
        ]
        state.finish(nodes)

        assert state.status == BridgesRequestStatus.FAILED

    def test_finish_with_no_active_sets_canceled(self):
        """测试 finish() 在没有活跃节点时设置为 CANCELED。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.CANCELED),
            self._create_mock_pipe_node(PipeStatus.CANCELED),
        ]
        state.finish(nodes)

        assert state.status == BridgesRequestStatus.CANCELED


# ──────────────────────────────────────────────────────────────────────────────
# TestProperties
# ──────────────────────────────────────────────────────────────────────────────


class TestProperties:
    def test_duration_seconds_is_none_when_not_finished(self):
        """测试未完成时 duration_seconds 为 None。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        assert state.duration_seconds is None

    def test_succeeded_is_true_when_done(self):
        """测试 succeeded 在 DONE 状态下为 True。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        state.status = BridgesRequestStatus.DONE
        assert state.succeeded is True

    def test_succeeded_is_false_when_not_done(self):
        """测试 succeeded 在非 DONE 状态下为 False。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        state.status = BridgesRequestStatus.FAILED
        assert state.succeeded is False

    def test_start_at_repr_returns_iso_format(self):
        """测试 start_at_repr 返回 ISO 格式。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        nodes = []
        state.start(nodes)

        assert state.start_at_repr is not None
        assert "T" in state.start_at_repr  # ISO format contains 'T'


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        result = state.export()
        assert isinstance(result, dict)

    def test_export_contains_request_id(self):
        """测试导出包含 request_id。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        result = state.export()
        assert result["request_id"] == request.id

    def test_export_contains_status(self):
        """测试导出包含 status。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        result = state.export()
        assert result["status"] == "PENDING"

    def test_export_contains_pipes_summary(self):
        """测试导出包含 pipes 汇总。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        result = state.export()
        assert "pipes" in result
        assert "total" in result["pipes"]
        assert "success" in result["pipes"]

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        result = state.describe()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_report_returns_dict(self):
        """测试 report() 返回字典。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        result = state.report()
        assert isinstance(result, dict)

    def test_report_contains_pipe_nodes_list(self):
        """测试 report() 包含 pipe_nodes 列表。"""
        request = BridgesRequest()
        state = BridgesRequestState(request=request)
        result = state.report()
        assert "pipe_nodes" in result
        assert isinstance(result["pipe_nodes"], list)
