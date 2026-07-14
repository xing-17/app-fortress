"""
综合测试：app.bridges.sources.node

覆盖范围
--------
- TestSourceNode       实例化、属性访问
- TestNodeRun          run() 方法的基本流程
- TestNodeCancel       cancel() 取消功能
- TestNodeState        状态更新和追踪
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import polars as pl

from app.bridges.sources.context import SourceContext
from app.bridges.sources.node import SourceNode
from app.bridges.sources.state import SourceStatus

# ── 测试数据准备 ──────────────────────────────────────────────────────────────


def _create_mock_context():
    context = MagicMock(spec=SourceContext)
    context.id = "sctx_test123"
    context.request_id = "req_123"
    context.pipeline_id = "pipe_456"

    # Mock provider
    provider = MagicMock()
    provider.name = "mock_provider"
    context.provider = provider

    # Mock source with setting
    source = MagicMock()
    source.name = "mock_source"
    source.setting = MagicMock()
    source.setting.quality_enabled = False
    source.setting.primary_fields = []
    source.setting.partition = MagicMock()
    source.setting.partition.column = None
    source.setting.partition.prefix = None
    context.source = source

    # Mock destination
    dest = MagicMock()
    dest.name = "mock_dest"
    context.destinations = [dest]

    context.params = {}

    return context


# ──────────────────────────────────────────────────────────────────────────────
# TestSourceNode
# ──────────────────────────────────────────────────────────────────────────────


class TestSourceNode:
    def test_instantiation_from_context(self):
        """测试从 context 实例化。"""
        context = _create_mock_context()
        node = SourceNode(context)
        assert node.context == context
        assert node.id == context.id
        assert node.provider == context.provider
        assert node.source == context.source

    def test_state_is_initialized(self):
        """测试 state 初始化。"""
        context = _create_mock_context()
        node = SourceNode(context)
        assert node.state is not None
        assert node.state.status == SourceStatus.PENDING

    def test_quality_is_initialized(self):
        """测试 quality 初始化。"""
        context = _create_mock_context()
        node = SourceNode(context)
        assert node.quality is not None
        assert node.quality.source_name == context.source.name
        assert node.quality.source_context_id == context.id

    def test_destinations_accessible(self):
        """测试 destinations 可访问。"""
        context = _create_mock_context()
        node = SourceNode(context)
        assert len(node.destinations) == 1
        assert node.destinations[0].name == "mock_dest"

    def test_params_accessible(self):
        """测试 params 可访问。"""
        context = _create_mock_context()
        context.params = {"key": "value"}
        node = SourceNode(context)
        assert node.params == {"key": "value"}


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeRun
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeRun:
    def test_run_calls_invoke(self):
        """测试 run() 调用 invoke()。"""
        context = _create_mock_context()
        node = SourceNode(context)

        # Mock invoke to return data
        test_df = pl.DataFrame({"id": [1, 2, 3]})
        with patch.object(node, "invoke", return_value=test_df) as mock_invoke:
            with patch.object(node, "_write_data"), patch.object(node, "_write_quality"):
                state = node.run()
            mock_invoke.assert_called_once()

        assert state.status == SourceStatus.SUCCESS

    def test_run_calls_write_when_data_not_empty(self):
        """测试 run() 在数据非空时调用 _write_data() 和 _write_quality()。"""
        context = _create_mock_context()
        node = SourceNode(context)

        test_df = pl.DataFrame({"id": [1, 2, 3]})
        with patch.object(node, "invoke", return_value=test_df):
            with patch.object(node, "_write_data") as mock_write_data:
                with patch.object(node, "_write_quality") as mock_write_quality:
                    state = node.run()

        mock_write_data.assert_called_once()
        mock_write_quality.assert_called_once()
        assert state.rows == 3

    def test_run_does_not_call_write_when_empty(self):
        """测试 run() 在数据为空时不调用 _write_data() 和 _write_quality()。"""
        context = _create_mock_context()
        node = SourceNode(context)

        test_df = pl.DataFrame()
        with patch.object(node, "invoke", return_value=test_df):
            with patch.object(node, "_write_data") as mock_write_data:
                with patch.object(node, "_write_quality") as mock_write_quality:
                    state = node.run()

        mock_write_data.assert_not_called()
        mock_write_quality.assert_not_called()
        assert state.rows == 0

    def test_run_sets_state_to_success_on_completion(self):
        """测试 run() 完成时设置状态为 SUCCESS。"""
        context = _create_mock_context()
        node = SourceNode(context)

        test_df = pl.DataFrame({"id": [1, 2, 3]})
        with patch.object(node, "invoke", return_value=test_df):
            with patch.object(node, "_write_data"), patch.object(node, "_write_quality"):
                state = node.run()

        assert state.status == SourceStatus.SUCCESS
        assert state.succeeded is True

    def test_run_sets_state_to_failed_on_exception(self):
        """测试 run() 异常时设置状态为 FAILED。"""
        context = _create_mock_context()
        node = SourceNode(context)

        with patch.object(node, "invoke", side_effect=Exception("Test error")):
            state = node.run()

        assert state.status == SourceStatus.FAILED
        assert "Test error" in state.error

    def test_run_returns_state(self):
        """测试 run() 返回 state。"""
        context = _create_mock_context()
        node = SourceNode(context)

        test_df = pl.DataFrame()
        with patch.object(node, "invoke", return_value=test_df):
            state = node.run()

        assert state is not None
        assert state == node.state


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeCancel
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeCancel:
    def test_cancel_sets_event(self):
        """测试 cancel() 设置取消事件。"""
        context = _create_mock_context()
        node = SourceNode(context)

        node.cancel()
        assert node._is_cancelled() is True

    def test_run_checks_cancel_before_invoke(self):
        """测试 run() 在 invoke 前检查取消状态。"""
        context = _create_mock_context()
        node = SourceNode(context)

        node.cancel()
        state = node.run()

        assert state.status == SourceStatus.CANCELED

    def test_cancelled_node_does_not_invoke(self):
        """测试取消的节点不调用 invoke()。"""
        context = _create_mock_context()
        node = SourceNode(context)

        with patch.object(node, "invoke") as mock_invoke:
            node.cancel()
            _ = node.run()

        mock_invoke.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeState
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeState:
    def test_state_tracks_started_at(self):
        """测试 state 追踪开始时间。"""
        context = _create_mock_context()
        node = SourceNode(context)

        test_df = pl.DataFrame()
        with patch.object(node, "invoke", return_value=test_df):
            state = node.run()

        assert state.started_at is not None

    def test_state_tracks_finished_at(self):
        """测试 state 追踪结束时间。"""
        context = _create_mock_context()
        node = SourceNode(context)

        test_df = pl.DataFrame()
        with patch.object(node, "invoke", return_value=test_df):
            state = node.run()

        assert state.finished_at is not None

    def test_state_tracks_duration(self):
        """测试 state 追踪执行时长。"""
        context = _create_mock_context()
        node = SourceNode(context)

        test_df = pl.DataFrame()
        with patch.object(node, "invoke", return_value=test_df):
            state = node.run()

        assert state.duration_seconds is not None
        assert state.duration_seconds >= 0

    def test_state_tracks_row_count(self):
        """测试 state 追踪行数。"""
        context = _create_mock_context()
        node = SourceNode(context)

        test_df = pl.DataFrame({"id": [1, 2, 3]})
        with patch.object(node, "invoke", return_value=test_df):
            with patch.object(node, "_write_data"), patch.object(node, "_write_quality"):
                state = node.run()

        assert state.rows == 3
