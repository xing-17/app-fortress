"""
综合测试：app.bridges.pipelines.node

覆盖范围
--------
- TestPipeNode        实例化、属性访问
- TestNodeDerive      derive() 方法的节点派生
- TestNodeRun         run() 方法的基本流程
- TestNodeCancel      cancel() 取消功能
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from app.bridges.pipelines.context import PipeContext
from app.bridges.pipelines.node import PipeNode
from app.bridges.pipelines.state import PipeStatus
from app.bridges.sources.node import SourceNode
from app.bridges.sources.state import SourceStatus

# ── 测试数据准备 ──────────────────────────────────────────────────────────────


def _create_mock_provider():
    """创建符合 BaseProvider 接口的 mock 对象"""
    from app.bridges.resources.providers.base.provider import BaseProvider

    provider = Mock(spec=BaseProvider)
    provider.name = "mock_provider"
    provider.setting = Mock()
    provider.setting.max_threads = 1
    return provider


def _create_mock_source():
    """创建符合 BaseSource 接口的 mock 对象"""
    from app.bridges.resources.sources.base.source import BaseSource

    source = Mock(spec=BaseSource)
    source.name = "mock_source"
    source.setting = Mock()
    source.setting.provider_type = "mock_type"
    source.setting.strategy = "mock_strategy"
    return source


def _create_mock_destination():
    """创建符合 BaseDestination 接口的 mock 对象"""
    from app.bridges.resources.destinations.base.destination import BaseDestination

    dest = Mock(spec=BaseDestination)
    dest.name = "mock_dest"
    return dest


def _create_mock_context():
    """创建 mock PipeContext"""
    context = MagicMock(spec=PipeContext)
    context.id = "pctx_test123"
    context.request_id = "req_123"
    context.provider = _create_mock_provider()
    context.source = _create_mock_source()
    context.destinations = [_create_mock_destination()]
    context.params = {}
    return context


# ──────────────────────────────────────────────────────────────────────────────
# TestPipeNode
# ──────────────────────────────────────────────────────────────────────────────


class TestPipeNode:
    def test_instantiation_from_context(self):
        """测试从 context 实例化。"""
        context = _create_mock_context()
        node = PipeNode(context)
        assert node.context == context
        assert node.id == context.id
        assert node.request_id == context.request_id

    def test_state_is_initialized(self):
        """测试 state 初始化。"""
        context = _create_mock_context()
        node = PipeNode(context)
        assert node.state is not None
        assert node.state.status == PipeStatus.PENDING

    def test_source_nodes_is_empty_initially(self):
        """测试初始时 source_nodes 为空。"""
        context = _create_mock_context()
        node = PipeNode(context)
        assert node.source_nodes == []

    def test_cancel_event_is_initialized(self):
        """测试 cancel_event 初始化。"""
        context = _create_mock_context()
        node = PipeNode(context)
        assert node._cancel_event is not None
        assert not node._is_cancelled()


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeDerive
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeDerive:
    def test_derive_creates_source_nodes(self):
        """测试 derive() 创建源节点。"""
        context = _create_mock_context()
        node = PipeNode(context)

        # Mock StrategyFactory to return a mock strategy
        mock_strategy = Mock()
        mock_strategy.run.return_value = [
            {"param1": "value1"},
            {"param2": "value2"},
        ]

        with patch("app.bridges.pipelines.node.StrategyFactory.create", return_value=mock_strategy):
            source_nodes = node.derive()

        assert len(source_nodes) == 2
        assert all(isinstance(n, SourceNode) for n in source_nodes)

    def test_derive_returns_empty_when_no_params(self):
        """测试策略返回空参数时 derive() 返回空列表。"""
        context = _create_mock_context()
        node = PipeNode(context)

        mock_strategy = Mock()
        mock_strategy.run.return_value = []

        with patch("app.bridges.pipelines.node.StrategyFactory.create", return_value=mock_strategy):
            source_nodes = node.derive()

        assert source_nodes == []

    def test_derive_calls_strategy_with_correct_params(self):
        """测试 derive() 使用正确的参数调用策略。"""
        context = _create_mock_context()
        context.params = {"key": "value"}
        node = PipeNode(context)

        mock_strategy = Mock()
        mock_strategy.run.return_value = [{"param": "value"}]

        with patch("app.bridges.pipelines.node.StrategyFactory.create", return_value=mock_strategy):
            node.derive()

        mock_strategy.run.assert_called_once()
        call_kwargs = mock_strategy.run.call_args[1]
        assert call_kwargs["provider"] == context.provider
        assert call_kwargs["params"] == context.params


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeRun
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeRun:
    def test_run_starts_state(self):
        """测试 run() 启动状态。"""
        context = _create_mock_context()
        node = PipeNode(context)

        with patch.object(node, "derive", return_value=[]):
            state = node.run()

        assert state.status == PipeStatus.DONE
        assert state.started_at is not None

    def test_run_calls_derive(self):
        """测试 run() 调用 derive()。"""
        context = _create_mock_context()
        node = PipeNode(context)

        with patch.object(node, "derive", return_value=[]) as mock_derive:
            node.run()

        mock_derive.assert_called_once()

    def test_run_with_no_source_nodes_finishes_early(self):
        """测试没有源节点时 run() 提前完成。"""
        context = _create_mock_context()
        node = PipeNode(context)

        with patch.object(node, "derive", return_value=[]):
            state = node.run()

        assert state.finished_at is not None
        assert state.total == 0

    def test_run_sequential_when_max_threads_is_one(self):
        """测试 max_threads=1 时顺序运行。"""
        context = _create_mock_context()
        context.provider.setting.max_threads = 1
        node = PipeNode(context)

        mock_source_node = Mock(spec=SourceNode)
        mock_state = Mock()
        mock_state.status = SourceStatus.SUCCESS
        mock_source_node.state = mock_state
        mock_source_node.run.return_value = mock_state

        with patch.object(node, "derive", return_value=[mock_source_node]):
            with patch.object(node, "_run_sequential") as mock_sequential:
                node.run()

        mock_sequential.assert_called_once()

    def test_run_concurrent_when_max_threads_greater_than_one(self):
        """测试 max_threads>1 时并发运行。"""
        context = _create_mock_context()
        context.provider.setting.max_threads = 4
        node = PipeNode(context)

        mock_source_node = Mock(spec=SourceNode)
        mock_state = Mock()
        mock_state.status = SourceStatus.SUCCESS
        mock_source_node.state = mock_state

        with patch.object(node, "derive", return_value=[mock_source_node]):
            with patch.object(node, "_run_concurrent") as mock_concurrent:
                node.run()

        mock_concurrent.assert_called_once_with(4)

    def test_run_finishes_state_after_execution(self):
        """测试 run() 执行后完成状态。"""
        context = _create_mock_context()
        node = PipeNode(context)

        mock_source_node = Mock(spec=SourceNode)
        mock_state = Mock()
        mock_state.status = SourceStatus.SUCCESS
        mock_source_node.state = mock_state

        with patch.object(node, "derive", return_value=[mock_source_node]):
            with patch.object(mock_source_node, "run"):
                state = node.run()

        assert state.finished_at is not None
        assert state.total == 1


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeCancel
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeCancel:
    def test_cancel_sets_cancel_event(self):
        """测试 cancel() 设置取消事件。"""
        context = _create_mock_context()
        node = PipeNode(context)

        node.cancel()

        assert node._is_cancelled()

    def test_cancel_propagates_to_source_nodes(self):
        """测试 cancel() 传播到源节点。"""
        context = _create_mock_context()
        node = PipeNode(context)

        mock_source_node = Mock(spec=SourceNode)
        node.source_nodes = [mock_source_node]

        node.cancel()

        mock_source_node.cancel.assert_called_once()

    def test_cancelled_node_marks_pending_as_canceled(self):
        """测试取消节点时标记待运行节点为已取消。"""
        context = _create_mock_context()
        node = PipeNode(context)

        mock_source_node = Mock(spec=SourceNode)
        mock_source_node.state = Mock()
        mock_source_node.state.status = SourceStatus.PENDING

        # 设置为已取消
        node.cancel()

        # 使用 derive 返回 mock 节点
        with patch.object(node, "derive", return_value=[mock_source_node]):
            node.run()

        # 验证节点的 cancel 被调用
        mock_source_node.state.cancel.assert_called()


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        context = _create_mock_context()
        node = PipeNode(context)

        exported = node.export()
        assert isinstance(exported, dict)

    def test_export_contains_context_and_state(self):
        """测试 export() 包含 context 和 state。"""
        context = _create_mock_context()
        context.export = Mock(return_value={"id": "pctx_test123"})
        node = PipeNode(context)

        exported = node.export()
        assert "context" in exported
        assert "state" in exported

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        context = _create_mock_context()
        context.export = Mock(return_value={"id": "pctx_test123"})
        node = PipeNode(context)

        import json

        described = node.describe()
        assert isinstance(described, str)
        # 验证是有效的 JSON
        parsed = json.loads(described)
        assert isinstance(parsed, dict)
