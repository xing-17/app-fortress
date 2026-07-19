"""
综合测试：app.bridges.core._service.state

覆盖范围
--------
- TestCoreRequestStatus     枚举值检查
- TestCoreRequestState      初始状态、属性
- TestStateTransition       start/finish/cancel 状态转换
- TestStateUpdate           update() 方法和节点统计
- TestProgress              progress / progress_pct / eta_seconds 属性
- TestExport                export() 和 describe() 方法
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import Mock

from app.bridges.core._service.request import CoreRequest
from app.bridges.core._service.state import CoreRequestState, CoreRequestStatus
from app.bridges.core.pipeline.state import PipelineStatus
from app.bridges.core.pipenode.state import PipeNodeState, PipeNodeStatus

# ──────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────────────────────


def _make_request() -> CoreRequest:
    return CoreRequest()


def _create_mock_pipeline_node(status: PipelineStatus, pipenodes=None):
    """创建具有指定状态的 mock PipelineNode。"""
    node = Mock()
    node.state = Mock()
    node.state.status = status
    node.pipenodes = pipenodes or []
    return node


def _create_mock_pipenode(status: PipeNodeStatus, rows: int = 0):
    """创建具有指定状态的 mock PipeNode。"""
    pn = Mock()
    pn.state = PipeNodeState()
    pn.state.status = status
    pn.state.rows = rows
    return pn


# ──────────────────────────────────────────────────────────────────────────────
# TestCoreRequestStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestCoreRequestStatus:
    def test_status_enum_has_pending(self):
        """测试状态枚举包含 PENDING。"""
        assert hasattr(CoreRequestStatus, "PENDING")
        assert CoreRequestStatus.PENDING.value == "PENDING"

    def test_status_enum_has_running(self):
        """测试状态枚举包含 RUNNING。"""
        assert hasattr(CoreRequestStatus, "RUNNING")
        assert CoreRequestStatus.RUNNING.value == "RUNNING"

    def test_status_enum_has_done(self):
        """测试状态枚举包含 DONE。"""
        assert hasattr(CoreRequestStatus, "DONE")
        assert CoreRequestStatus.DONE.value == "DONE"

    def test_status_enum_has_partial(self):
        """测试状态枚举包含 PARTIAL。"""
        assert hasattr(CoreRequestStatus, "PARTIAL")
        assert CoreRequestStatus.PARTIAL.value == "PARTIAL"

    def test_status_enum_has_failed(self):
        """测试状态枚举包含 FAILED。"""
        assert hasattr(CoreRequestStatus, "FAILED")
        assert CoreRequestStatus.FAILED.value == "FAILED"

    def test_status_enum_has_canceled(self):
        """测试状态枚举包含 CANCELED。"""
        assert hasattr(CoreRequestStatus, "CANCELED")
        assert CoreRequestStatus.CANCELED.value == "CANCELED"


# ──────────────────────────────────────────────────────────────────────────────
# TestCoreRequestState
# ──────────────────────────────────────────────────────────────────────────────


class TestCoreRequestState:
    def test_initial_status_is_pending(self):
        """测试初始状态为 PENDING。"""
        state = CoreRequestState(request=_make_request())
        assert state.status == CoreRequestStatus.PENDING

    def test_initial_timestamps_are_none(self):
        """测试初始时间戳为 None。"""
        state = CoreRequestState(request=_make_request())
        assert state.started_at is None
        assert state.finished_at is None

    def test_initial_counts_are_zero(self):
        """测试初始计数全为 0。"""
        state = CoreRequestState(request=_make_request())
        assert state.total == 0
        assert state.done == 0
        assert state.failed == 0
        assert state.running == 0
        assert state.pending == 0
        assert state.canceled == 0
        assert state.partial == 0

    def test_initial_pipeline_nodes_is_empty(self):
        """测试初始 pipeline_nodes 为空列表。"""
        state = CoreRequestState(request=_make_request())
        assert state.pipeline_nodes == []

    def test_succeeded_is_false_initially(self):
        """测试初始时 succeeded 为 False。"""
        state = CoreRequestState(request=_make_request())
        assert state.succeeded is False

    def test_finished_is_false_initially(self):
        """测试初始时 finished 为 False。"""
        state = CoreRequestState(request=_make_request())
        assert state.finished is False

    def test_duration_is_none_when_not_finished(self):
        """测试未完成时 duration_seconds 为 None。"""
        state = CoreRequestState(request=_make_request())
        assert state.duration_seconds is None

    def test_total_rows_is_zero_initially(self):
        """测试初始时 total_rows 为 0。"""
        state = CoreRequestState(request=_make_request())
        assert state.total_rows == 0

    def test_pipe_nodes_is_empty_initially(self):
        """测试初始时 pipe_nodes 为空。"""
        state = CoreRequestState(request=_make_request())
        assert state.pipe_nodes == []


# ──────────────────────────────────────────────────────────────────────────────
# TestStateTransition
# ──────────────────────────────────────────────────────────────────────────────


class TestStateTransition:
    def test_start_sets_status_to_running(self):
        """测试 start() 将状态设置为 RUNNING。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.PENDING),
            _create_mock_pipeline_node(PipelineStatus.PENDING),
        ]
        state.start(nodes)
        assert state.status == CoreRequestStatus.RUNNING

    def test_start_sets_started_at(self):
        """测试 start() 设置 started_at。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        assert state.started_at is not None
        assert isinstance(state.started_at, datetime)

    def test_start_sets_total_and_pending(self):
        """测试 start() 设置 total 和 pending。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.PENDING),
            _create_mock_pipeline_node(PipelineStatus.PENDING),
            _create_mock_pipeline_node(PipelineStatus.PENDING),
        ]
        state.start(nodes)
        assert state.total == 3
        assert state.pending == 3

    def test_cancel_sets_status_to_canceled(self):
        """测试 cancel() 将状态设置为 CANCELED。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        state.cancel()
        assert state.status == CoreRequestStatus.CANCELED

    def test_cancel_sets_finished_at(self):
        """测试 cancel() 设置 finished_at。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        state.cancel()
        assert state.finished_at is not None

    def test_finish_sets_status_done_when_all_done(self):
        """测试 finish() 在全部 DONE 时设置状态为 DONE。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.DONE),
            _create_mock_pipeline_node(PipelineStatus.DONE),
        ]
        state.finish(nodes)
        assert state.status == CoreRequestStatus.DONE

    def test_finish_sets_status_partial_when_mixed(self):
        """测试 finish() 在部分成功时设置状态为 PARTIAL。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.DONE),
            _create_mock_pipeline_node(PipelineStatus.FAILED),
        ]
        state.finish(nodes)
        assert state.status == CoreRequestStatus.PARTIAL

    def test_finish_sets_status_failed_when_all_failed(self):
        """测试 finish() 在全部失败时设置状态为 FAILED。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.FAILED),
            _create_mock_pipeline_node(PipelineStatus.FAILED),
        ]
        state.finish(nodes)
        assert state.status == CoreRequestStatus.FAILED

    def test_finish_sets_finished_at(self):
        """测试 finish() 设置 finished_at。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        nodes = [_create_mock_pipeline_node(PipelineStatus.DONE)]
        state.finish(nodes)
        assert state.finished_at is not None

    def test_finish_does_not_override_canceled_status(self):
        """测试 finish() 不覆盖 CANCELED 状态。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        state.cancel()
        nodes = [_create_mock_pipeline_node(PipelineStatus.DONE)]
        state.finish(nodes)
        assert state.status == CoreRequestStatus.CANCELED

    def test_succeeded_is_true_after_done_finish(self):
        """测试全部完成后 succeeded 为 True。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        nodes = [_create_mock_pipeline_node(PipelineStatus.DONE)]
        state.finish(nodes)
        assert state.succeeded is True

    def test_finished_is_true_after_finish(self):
        """测试 finish() 后 finished 为 True。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        nodes = [_create_mock_pipeline_node(PipelineStatus.DONE)]
        state.finish(nodes)
        assert state.finished is True

    def test_finished_is_true_after_cancel(self):
        """测试 cancel() 后 finished 为 True。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        state.cancel()
        assert state.finished is True


# ──────────────────────────────────────────────────────────────────────────────
# TestStateUpdate
# ──────────────────────────────────────────────────────────────────────────────


class TestStateUpdate:
    def test_update_counts_total(self):
        """测试 update() 统计总数。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.DONE),
            _create_mock_pipeline_node(PipelineStatus.FAILED),
            _create_mock_pipeline_node(PipelineStatus.PENDING),
        ]
        state.update(nodes)
        assert state.total == 3

    def test_update_counts_done(self):
        """测试 update() 统计 DONE 数。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.DONE),
            _create_mock_pipeline_node(PipelineStatus.DONE),
            _create_mock_pipeline_node(PipelineStatus.FAILED),
        ]
        state.update(nodes)
        assert state.done == 2

    def test_update_counts_failed(self):
        """测试 update() 统计 FAILED 数。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.DONE),
            _create_mock_pipeline_node(PipelineStatus.FAILED),
            _create_mock_pipeline_node(PipelineStatus.FAILED),
        ]
        state.update(nodes)
        assert state.failed == 2

    def test_update_counts_running(self):
        """测试 update() 统计 RUNNING 数。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.RUNNING),
            _create_mock_pipeline_node(PipelineStatus.DONE),
        ]
        state.update(nodes)
        assert state.running == 1

    def test_update_counts_pending(self):
        """测试 update() 统计 PENDING 数。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.PENDING),
            _create_mock_pipeline_node(PipelineStatus.PENDING),
            _create_mock_pipeline_node(PipelineStatus.DONE),
        ]
        state.update(nodes)
        assert state.pending == 2

    def test_update_counts_canceled(self):
        """测试 update() 统计 CANCELED 数。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.CANCELED),
            _create_mock_pipeline_node(PipelineStatus.DONE),
        ]
        state.update(nodes)
        assert state.canceled == 1

    def test_update_counts_partial(self):
        """测试 update() 统计 PARTIAL 数。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.PARTIAL),
            _create_mock_pipeline_node(PipelineStatus.DONE),
        ]
        state.update(nodes)
        assert state.partial == 1

    def test_update_with_empty_nodes(self):
        """测试 update() 处理空节点列表。"""
        state = CoreRequestState(request=_make_request())
        state.update([])
        assert state.total == 0
        assert state.done == 0
        assert state.failed == 0


# ──────────────────────────────────────────────────────────────────────────────
# TestProgress
# ──────────────────────────────────────────────────────────────────────────────


class TestProgress:
    def test_progress_is_0_when_no_nodes(self):
        """测试无节点时 progress 为 0.0。"""
        state = CoreRequestState(request=_make_request())
        assert state.progress == 0.0

    def test_progress_pct_is_0_when_no_nodes(self):
        """测试无节点时 progress_pct 为 0.0。"""
        state = CoreRequestState(request=_make_request())
        assert state.progress_pct == 0.0

    def test_progress_based_on_pipeline_node_counts(self):
        """测试基于 pipeline_node 维度计算 progress（无 pipenodes 展开时）。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.DONE),
            _create_mock_pipeline_node(PipelineStatus.PENDING),
        ]
        state.update(nodes)
        # done=1, partial=0, failed=0, canceled=0, total=2 → 1/2 = 0.5
        assert state.progress == 0.5

    def test_progress_based_on_pipenodes_when_available(self):
        """测试有 pipenodes 时基于 PipeNode 维度计算 progress。"""
        state = CoreRequestState(request=_make_request())
        pn_done = _create_mock_pipenode(PipeNodeStatus.DONE)
        pn_pending = _create_mock_pipenode(PipeNodeStatus.PENDING)
        node = _create_mock_pipeline_node(PipelineStatus.RUNNING, pipenodes=[pn_done, pn_pending])
        state.pipeline_nodes = [node]
        # 1 done out of 2 pipenodes → 0.5
        assert state.progress == 0.5

    def test_progress_pct_is_50_for_half_done(self):
        """测试一半完成时 progress_pct 为 50.0。"""
        state = CoreRequestState(request=_make_request())
        nodes = [
            _create_mock_pipeline_node(PipelineStatus.DONE),
            _create_mock_pipeline_node(PipelineStatus.PENDING),
        ]
        state.update(nodes)
        assert state.progress_pct == 50.0

    def test_eta_is_none_before_start(self):
        """测试未开始时 eta_seconds 为 None。"""
        state = CoreRequestState(request=_make_request())
        assert state.eta_seconds is None

    def test_eta_is_0_after_finish(self):
        """测试完成后 eta_seconds 为 0.0。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        nodes = [_create_mock_pipeline_node(PipelineStatus.DONE)]
        state.finish(nodes)
        assert state.eta_seconds == 0.0

    def test_elapsed_seconds_none_before_start(self):
        """测试未开始时 elapsed_seconds 为 None。"""
        state = CoreRequestState(request=_make_request())
        assert state.elapsed_seconds is None

    def test_elapsed_seconds_set_after_start(self):
        """测试开始后 elapsed_seconds 为浮点数。"""
        state = CoreRequestState(request=_make_request())
        state.start([])
        assert state.elapsed_seconds is not None
        assert isinstance(state.elapsed_seconds, float)

    def test_total_rows_sums_all_pipenodes(self):
        """测试 total_rows 汇总所有 pipenodes 的 rows。"""
        state = CoreRequestState(request=_make_request())
        pn1 = _create_mock_pipenode(PipeNodeStatus.DONE, rows=100)
        pn2 = _create_mock_pipenode(PipeNodeStatus.DONE, rows=50)
        node = _create_mock_pipeline_node(PipelineStatus.DONE, pipenodes=[pn1, pn2])
        state.pipeline_nodes = [node]
        assert state.total_rows == 150

    def test_pipe_nodes_flattens_all_pipenodes(self):
        """测试 pipe_nodes 展开所有 PipelineNode 下的 pipenodes。"""
        state = CoreRequestState(request=_make_request())
        pn1 = _create_mock_pipenode(PipeNodeStatus.DONE)
        pn2 = _create_mock_pipenode(PipeNodeStatus.DONE)
        pn3 = _create_mock_pipenode(PipeNodeStatus.PENDING)
        node1 = _create_mock_pipeline_node(PipelineStatus.DONE, pipenodes=[pn1, pn2])
        node2 = _create_mock_pipeline_node(PipelineStatus.PENDING, pipenodes=[pn3])
        state.pipeline_nodes = [node1, node2]
        assert len(state.pipe_nodes) == 3


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        state = CoreRequestState(request=_make_request())
        result = state.export()
        assert isinstance(result, dict)

    def test_export_contains_counts(self):
        """测试 export() 包含 counts 字段。"""
        state = CoreRequestState(request=_make_request())
        result = state.export()
        assert "counts" in result
        counts = result["counts"]
        assert "total" in counts
        assert "done" in counts
        assert "failed" in counts
        assert "running" in counts
        assert "pending" in counts
        assert "partial" in counts
        assert "canceled" in counts

    def test_export_contains_progress(self):
        """测试 export() 包含 progress 字段。"""
        state = CoreRequestState(request=_make_request())
        result = state.export()
        assert "progress" in result
        progress = result["progress"]
        assert "progress" in progress
        assert "progress_pct" in progress
        assert "eta_seconds" in progress
        assert "elapsed_seconds" in progress

    def test_export_contains_status(self):
        """测试 export() 包含 status 字段。"""
        state = CoreRequestState(request=_make_request())
        result = state.export()
        assert result["status"] == "PENDING"

    def test_describe_returns_valid_json(self):
        """测试 describe() 返回有效 JSON 字符串。"""
        state = CoreRequestState(request=_make_request())
        result = state.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert "counts" in parsed
        assert "progress" in parsed
