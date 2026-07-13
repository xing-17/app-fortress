"""
综合测试：app.bridges.pipelines.state

覆盖范围
--------
- TestPipeStatus       枚举值检查
- TestPipeState        状态转换、属性计算
- TestStateTransition  start/finish/cancel 状态转换
- TestExport           export() 和 describe() 方法
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock

from app.bridges.pipelines.state import PipeState, PipeStatus
from app.bridges.sources.state import SourceStatus

# ──────────────────────────────────────────────────────────────────────────────
# TestPipeStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestPipeStatus:
    def test_status_enum_has_pending(self):
        """测试状态枚举包含 PENDING。"""
        assert hasattr(PipeStatus, "PENDING")
        assert PipeStatus.PENDING.value == "PENDING"

    def test_status_enum_has_running(self):
        """测试状态枚举包含 RUNNING。"""
        assert hasattr(PipeStatus, "RUNNING")
        assert PipeStatus.RUNNING.value == "RUNNING"

    def test_status_enum_has_done(self):
        """测试状态枚举包含 DONE。"""
        assert hasattr(PipeStatus, "DONE")
        assert PipeStatus.DONE.value == "DONE"

    def test_status_enum_has_partial(self):
        """测试状态枚举包含 PARTIAL。"""
        assert hasattr(PipeStatus, "PARTIAL")
        assert PipeStatus.PARTIAL.value == "PARTIAL"

    def test_status_enum_has_failed(self):
        """测试状态枚举包含 FAILED。"""
        assert hasattr(PipeStatus, "FAILED")
        assert PipeStatus.FAILED.value == "FAILED"

    def test_status_enum_has_canceled(self):
        """测试状态枚举包含 CANCELED。"""
        assert hasattr(PipeStatus, "CANCELED")
        assert PipeStatus.CANCELED.value == "CANCELED"


# ──────────────────────────────────────────────────────────────────────────────
# TestPipeState
# ──────────────────────────────────────────────────────────────────────────────


class TestPipeState:
    def test_initial_status_is_pending(self):
        """测试初始状态为 PENDING。"""
        state = PipeState()
        assert state.status == PipeStatus.PENDING

    def test_initial_timestamps_are_none(self):
        """测试初始时间戳为 None。"""
        state = PipeState()
        assert state.started_at is None
        assert state.finished_at is None

    def test_initial_counters_are_zero(self):
        """测试初始计数器为 0。"""
        state = PipeState()
        assert state.total == 0
        assert state.success == 0
        assert state.failed == 0
        assert state.running == 0
        assert state.pending == 0
        assert state.canceled == 0

    def test_duration_is_none_when_not_finished(self):
        """测试未完成时 duration 为 None。"""
        state = PipeState()
        assert state.duration_seconds is None

    def test_succeeded_is_false_initially(self):
        """测试初始时 succeeded 为 False。"""
        state = PipeState()
        assert state.succeeded is False


# ──────────────────────────────────────────────────────────────────────────────
# TestStateTransition
# ──────────────────────────────────────────────────────────────────────────────


class TestStateTransition:
    def test_start_sets_status_to_running(self):
        """测试 start() 将状态设置为 RUNNING。"""
        state = PipeState()
        state.start()
        assert state.status == PipeStatus.RUNNING

    def test_start_sets_started_at(self):
        """测试 start() 设置 started_at。"""
        state = PipeState()
        state.start()
        assert state.started_at is not None
        assert isinstance(state.started_at, datetime)

    def test_cancel_sets_status_to_canceled(self):
        """测试 cancel() 将状态设置为 CANCELED。"""
        state = PipeState()
        state.cancel()
        assert state.status == PipeStatus.CANCELED

    def test_cancel_sets_finished_at(self):
        """测试 cancel() 设置 finished_at。"""
        state = PipeState()
        state.cancel()
        assert state.finished_at is not None
        assert isinstance(state.finished_at, datetime)

    def test_update_counts_source_nodes(self):
        """测试 update() 统计源节点状态。"""
        state = PipeState()

        # 创建 mock source nodes
        nodes = []
        for status in [
            SourceStatus.SUCCESS,
            SourceStatus.SUCCESS,
            SourceStatus.FAILED,
            SourceStatus.PENDING,
            SourceStatus.RUNNING,
        ]:
            node = MagicMock()
            node.state.status = status
            nodes.append(node)

        state.update(nodes)

        assert state.total == 5
        assert state.success == 2
        assert state.failed == 1
        assert state.pending == 1
        assert state.running == 1
        assert state.canceled == 0

    def test_finish_with_all_success_sets_done(self):
        """测试所有成功时 finish() 设置为 DONE。"""
        state = PipeState()
        state.start()

        nodes = []
        for _ in range(3):
            node = MagicMock()
            node.state.status = SourceStatus.SUCCESS
            nodes.append(node)

        state.finish(nodes)

        assert state.status == PipeStatus.DONE
        assert state.finished_at is not None

    def test_finish_with_all_failed_sets_failed(self):
        """测试所有失败时 finish() 设置为 FAILED。"""
        state = PipeState()
        state.start()

        nodes = []
        for _ in range(3):
            node = MagicMock()
            node.state.status = SourceStatus.FAILED
            nodes.append(node)

        state.finish(nodes)

        assert state.status == PipeStatus.FAILED

    def test_finish_with_partial_success_sets_partial(self):
        """测试部分成功时 finish() 设置为 PARTIAL。"""
        state = PipeState()
        state.start()

        nodes = []
        # 2 success, 1 failed
        for status in [SourceStatus.SUCCESS, SourceStatus.SUCCESS, SourceStatus.FAILED]:
            node = MagicMock()
            node.state.status = status
            nodes.append(node)

        state.finish(nodes)

        assert state.status == PipeStatus.PARTIAL

    def test_finish_with_empty_nodes_sets_done(self):
        """测试空节点列表时 finish() 设置为 DONE。"""
        state = PipeState()
        state.start()

        state.finish([])

        assert state.status == PipeStatus.DONE
        assert state.total == 0

    def test_finish_with_all_canceled_sets_canceled(self):
        """测试所有取消时 finish() 设置为 CANCELED。"""
        state = PipeState()
        state.start()

        nodes = []
        for _ in range(3):
            node = MagicMock()
            node.state.status = SourceStatus.CANCELED
            nodes.append(node)

        state.finish(nodes)

        assert state.status == PipeStatus.CANCELED


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        state = PipeState()
        exported = state.export()
        assert isinstance(exported, dict)

    def test_export_contains_status(self):
        """测试 export() 包含 status。"""
        state = PipeState()
        exported = state.export()
        assert "status" in exported
        assert exported["status"] == "PENDING"

    def test_export_contains_timestamps(self):
        """测试 export() 包含时间戳。"""
        state = PipeState()
        state.start()
        exported = state.export()
        assert "started_at" in exported
        assert "finished_at" in exported
        assert exported["started_at"] is not None
        assert exported["finished_at"] is None

    def test_export_contains_counters(self):
        """测试 export() 包含计数器。"""
        state = PipeState()
        exported = state.export()
        assert "total" in exported
        assert "success" in exported
        assert "failed" in exported
        assert "running" in exported
        assert "pending" in exported
        assert "canceled" in exported

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        state = PipeState()
        described = state.describe()
        assert isinstance(described, str)
        # 验证是有效的 JSON
        parsed = json.loads(described)
        assert isinstance(parsed, dict)

    def test_succeeded_is_true_when_done(self):
        """测试 DONE 状态时 succeeded 为 True。"""
        state = PipeState()
        state.status = PipeStatus.DONE
        assert state.succeeded is True

    def test_succeeded_is_false_when_not_done(self):
        """测试非 DONE 状态时 succeeded 为 False。"""
        state = PipeState()
        state.status = PipeStatus.PARTIAL
        assert state.succeeded is False

    def test_duration_calculated_when_finished(self):
        """测试完成时能计算 duration。"""
        state = PipeState()
        state.start()
        state.cancel()
        assert state.duration_seconds is not None
        assert state.duration_seconds >= 0
