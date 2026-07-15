"""
综合测试：app.bridges.core.state

覆盖范围
--------
- TestBridgesRequestStatus   枚举值检查
- TestBridgesRequestState    状态转换、属性计算
- TestStateTransition        start/update/finish/cancel 状态转换
- TestExport                 export()、describe()、report() 方法
"""

from __future__ import annotations

import json
import time
from unittest.mock import Mock

from app.bridges.core.request import BridgesCoreRequest
from app.bridges.core.state import BridgesCoreRequestState, BridgesCoreRequestStatus
from app.bridges.pipelines.state import PipeStatus
from app.bridges.sources.state import SourceStatus

# ──────────────────────────────────────────────────────────────────────────────
# TestBridgesRequestStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgesRequestStatus:
    def test_status_enum_has_pending(self):
        """测试状态枚举包含 PENDING。"""
        assert hasattr(BridgesCoreRequestStatus, "PENDING")
        assert BridgesCoreRequestStatus.PENDING.value == "PENDING"

    def test_status_enum_has_running(self):
        """测试状态枚举包含 RUNNING。"""
        assert hasattr(BridgesCoreRequestStatus, "RUNNING")
        assert BridgesCoreRequestStatus.RUNNING.value == "RUNNING"

    def test_status_enum_has_done(self):
        """测试状态枚举包含 DONE。"""
        assert hasattr(BridgesCoreRequestStatus, "DONE")
        assert BridgesCoreRequestStatus.DONE.value == "DONE"

    def test_status_enum_has_partial(self):
        """测试状态枚举包含 PARTIAL。"""
        assert hasattr(BridgesCoreRequestStatus, "PARTIAL")
        assert BridgesCoreRequestStatus.PARTIAL.value == "PARTIAL"

    def test_status_enum_has_failed(self):
        """测试状态枚举包含 FAILED。"""
        assert hasattr(BridgesCoreRequestStatus, "FAILED")
        assert BridgesCoreRequestStatus.FAILED.value == "FAILED"

    def test_status_enum_has_canceled(self):
        """测试状态枚举包含 CANCELED。"""
        assert hasattr(BridgesCoreRequestStatus, "CANCELED")
        assert BridgesCoreRequestStatus.CANCELED.value == "CANCELED"


# ──────────────────────────────────────────────────────────────────────────────
# TestBridgesRequestState
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgesRequestState:
    def test_initial_status_is_pending(self):
        """测试初始状态为 PENDING。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        assert state.status == BridgesCoreRequestStatus.PENDING

    def test_initial_timestamps_are_none(self):
        """测试初始时间戳为 None。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        assert state.started_at is None
        assert state.finished_at is None

    def test_initial_counters_are_zero(self):
        """测试初始计数器为 0。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        assert state.total == 0
        assert state.success == 0
        assert state.partial == 0
        assert state.failed == 0
        assert state.running == 0
        assert state.pending == 0
        assert state.canceled == 0

    def test_initial_pipe_nodes_is_empty(self):
        """测试初始 pipe_nodes 为空列表。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
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
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)

        nodes = [self._create_mock_pipe_node(PipeStatus.PENDING)]
        state.start(nodes)

        assert state.status == BridgesCoreRequestStatus.RUNNING
        assert state.started_at is not None

    def test_start_sets_total_and_pending(self):
        """测试 start() 设置 total 和 pending。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)

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
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)

        state.cancel()

        assert state.status == BridgesCoreRequestStatus.CANCELED
        assert state.finished_at is not None

    def test_is_cancelled_returns_true_when_canceled(self):
        """测试 _is_cancelled() 在取消后返回 True。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)

        assert state._is_cancelled() is False
        state.cancel()
        assert state._is_cancelled() is True

    def test_update_counts_nodes_by_status(self):
        """测试 update() 按状态计数节点。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)

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
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.DONE),
            self._create_mock_pipe_node(PipeStatus.DONE),
        ]
        state.finish(nodes)

        assert state.status == BridgesCoreRequestStatus.DONE
        assert state.finished_at is not None

    def test_finish_with_partial_and_success_sets_done(self):
        """测试 finish() 在部分成功+全部成功时设置为 DONE。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.DONE),
            self._create_mock_pipe_node(PipeStatus.PARTIAL),
        ]
        state.finish(nodes)

        assert state.status == BridgesCoreRequestStatus.DONE

    def test_finish_with_success_and_failure_sets_partial(self):
        """测试 finish() 在成功+失败时设置为 PARTIAL。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.DONE),
            self._create_mock_pipe_node(PipeStatus.FAILED),
        ]
        state.finish(nodes)

        assert state.status == BridgesCoreRequestStatus.PARTIAL

    def test_finish_with_all_failed_sets_failed(self):
        """测试 finish() 在全部失败时设置为 FAILED。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.FAILED),
            self._create_mock_pipe_node(PipeStatus.FAILED),
        ]
        state.finish(nodes)

        assert state.status == BridgesCoreRequestStatus.FAILED

    def test_finish_with_no_active_sets_canceled(self):
        """测试 finish() 在没有活跃节点时设置为 CANCELED。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)

        nodes = [
            self._create_mock_pipe_node(PipeStatus.CANCELED),
            self._create_mock_pipe_node(PipeStatus.CANCELED),
        ]
        state.finish(nodes)

        assert state.status == BridgesCoreRequestStatus.CANCELED


# ──────────────────────────────────────────────────────────────────────────────
# TestProperties
# ──────────────────────────────────────────────────────────────────────────────


class TestProperties:
    def test_duration_seconds_is_none_when_not_finished(self):
        """测试未完成时 duration_seconds 为 None。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        assert state.duration_seconds is None

    def test_succeeded_is_true_when_done(self):
        """测试 succeeded 在 DONE 状态下为 True。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        state.status = BridgesCoreRequestStatus.DONE
        assert state.succeeded is True

    def test_succeeded_is_false_when_not_done(self):
        """测试 succeeded 在非 DONE 状态下为 False。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        state.status = BridgesCoreRequestStatus.FAILED
        assert state.succeeded is False

    def test_start_at_repr_returns_iso_format(self):
        """测试 start_at_repr 返回 ISO 格式。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
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
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        result = state.export()
        assert isinstance(result, dict)

    def test_export_contains_request_id(self):
        """测试导出包含 request_id。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        result = state.export()
        assert result["request_id"] == request.id

    def test_export_contains_status(self):
        """测试导出包含 status。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        result = state.export()
        assert result["status"] == "PENDING"

    def test_export_contains_pipes_summary(self):
        """测试导出包含 pipes 汇总。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        result = state.export()
        assert "pipes" in result
        assert "total" in result["pipes"]
        assert "success" in result["pipes"]

    def test_export_contains_progress_fields(self):
        """测试导出包含进度相关字段。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        result = state.export()
        assert "elapsed_seconds" in result
        assert "progress" in result
        assert "progress_pct" in result
        assert "eta_seconds" in result

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        result = state.describe()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


# ──────────────────────────────────────────────────────────────────────────────
# TestProgressAndETA
# ──────────────────────────────────────────────────────────────────────────────


class TestProgressAndETA:
    """测试进度和 ETA 相关功能。"""

    def _create_mock_pipe_node_with_source_nodes(self, source_statuses: list[SourceStatus]):
        """创建包含指定状态 source nodes 的 mock PipeNode。"""
        source_nodes = []
        for status in source_statuses:
            mock_source_state = Mock()
            mock_source_state.status = status
            mock_source_state.rows = 100
            mock_source_node = Mock()
            mock_source_node.state = mock_source_state
            source_nodes.append(mock_source_node)

        # 根据 source nodes 推导 pipe 状态
        success = sum(1 for s in source_statuses if s == SourceStatus.SUCCESS)
        failed = sum(1 for s in source_statuses if s == SourceStatus.FAILED)
        if success > 0 and failed == 0:
            pipe_status = PipeStatus.DONE
        elif success > 0 and failed > 0:
            pipe_status = PipeStatus.PARTIAL
        elif failed > 0:
            pipe_status = PipeStatus.FAILED
        else:
            pipe_status = PipeStatus.RUNNING

        mock_pipe_state = Mock()
        mock_pipe_state.status = pipe_status
        mock_pipe_node = Mock()
        mock_pipe_node.state = mock_pipe_state
        mock_pipe_node.source_nodes = source_nodes
        return mock_pipe_node

    def test_elapsed_seconds_is_none_before_start(self):
        """测试启动前 elapsed_seconds 为 None。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        assert state.elapsed_seconds is None

    def test_elapsed_seconds_returns_value_after_start(self):
        """测试启动后 elapsed_seconds 返回有效值。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        state.start([])
        time.sleep(0.1)  # 等待一小段时间
        assert state.elapsed_seconds is not None
        assert state.elapsed_seconds > 0

    def test_elapsed_seconds_uses_finished_at_when_done(self):
        """测试完成后 elapsed_seconds 使用 finished_at。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        nodes = []
        state.start(nodes)
        time.sleep(0.1)
        state.finish(nodes)
        elapsed = state.elapsed_seconds
        assert elapsed is not None
        time.sleep(0.1)
        # 完成后再次查询，elapsed_seconds 应该不变
        assert state.elapsed_seconds == elapsed

    def test_progress_is_1_when_no_nodes(self):
        """测试无节点时 progress 为 1.0。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        assert state.progress == 1.0

    def test_progress_uses_pipe_nodes_when_no_source_nodes(self):
        """测试没有 source nodes 时使用 pipe nodes 计算进度。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        nodes = [
            self._create_mock_pipe_node_with_source_nodes([]),  # 空的 source_nodes
            self._create_mock_pipe_node_with_source_nodes([]),
            self._create_mock_pipe_node_with_source_nodes([]),
        ]
        # 手动设置 pipe 状态
        nodes[0].state.status = PipeStatus.DONE
        nodes[1].state.status = PipeStatus.RUNNING
        nodes[2].state.status = PipeStatus.PENDING

        state.start(nodes)
        state.update(nodes)
        # 1 完成 / 3 总数 = 0.333...
        assert 0.33 <= state.progress <= 0.34

    def test_progress_uses_source_nodes_when_available(self):
        """测试有 source nodes 时使用其计算进度。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        nodes = [
            self._create_mock_pipe_node_with_source_nodes(
                [
                    SourceStatus.SUCCESS,
                    SourceStatus.SUCCESS,
                    SourceStatus.RUNNING,
                    SourceStatus.PENDING,
                ]
            ),
        ]
        state.start(nodes)
        state.update(nodes)
        # 2 完成 / 4 总数 = 0.5
        assert state.progress == 0.5

    def test_progress_pct_returns_percentage(self):
        """测试 progress_pct 返回百分比。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        nodes = [
            self._create_mock_pipe_node_with_source_nodes(
                [
                    SourceStatus.SUCCESS,
                    SourceStatus.PENDING,
                ]
            ),
        ]
        state.start(nodes)
        state.update(nodes)
        # 1/2 = 0.5 = 50.0%
        assert state.progress_pct == 50.0

    def test_eta_seconds_is_none_before_start(self):
        """测试启动前 eta_seconds 为 None。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        assert state.eta_seconds is None

    def test_eta_seconds_is_none_when_no_progress(self):
        """测试无进度时 eta_seconds 为 None。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        nodes = [
            self._create_mock_pipe_node_with_source_nodes(
                [
                    SourceStatus.PENDING,
                    SourceStatus.PENDING,
                ]
            ),
        ]
        state.start(nodes)
        state.update(nodes)
        # progress = 0，无法推算 ETA
        assert state.eta_seconds is None

    def test_eta_seconds_returns_estimate_with_progress(self):
        """测试有进度时 eta_seconds 返回估算值。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        nodes = [
            self._create_mock_pipe_node_with_source_nodes(
                [
                    SourceStatus.SUCCESS,
                    SourceStatus.PENDING,
                ]
            ),
        ]
        state.start(nodes)
        time.sleep(0.1)
        state.update(nodes)
        # progress = 0.5，已用 0.1s，预计还需 0.1s
        eta = state.eta_seconds
        assert eta is not None
        assert eta > 0

    def test_eta_seconds_is_zero_when_finished(self):
        """测试完成后 eta_seconds 为 0.0。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        nodes = [
            self._create_mock_pipe_node_with_source_nodes(
                [
                    SourceStatus.SUCCESS,
                    SourceStatus.SUCCESS,
                ]
            ),
        ]
        state.start(nodes)
        state.finish(nodes)
        assert state.eta_seconds == 0.0

    def test_report_returns_dict(self):
        """测试 report() 返回字典。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        result = state.report()
        assert isinstance(result, dict)

    def test_report_contains_pipe_nodes_list(self):
        """测试 report() 包含 pipe_nodes 列表。"""
        request = BridgesCoreRequest()
        state = BridgesCoreRequestState(request=request)
        result = state.report()
        assert "pipe_nodes" in result
        assert isinstance(result["pipe_nodes"], list)
