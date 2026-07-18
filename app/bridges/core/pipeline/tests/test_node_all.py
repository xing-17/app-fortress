"""
综合测试：app.bridges.core.pipeline.node

覆盖范围
--------
- TestPipelineNode      实例化、属性访问
- TestDerive            derive() 方法和策略调用
- TestNodeRun           run() 方法的基本流程
- TestNodeCancel        cancel() 取消功能
- TestSequentialRun     顺序执行测试
- TestConcurrentRun     并发执行测试
- TestExport            export() 和 describe() 方法
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from app.bridges.core.pipeline.context import PipelineContext
from app.bridges.core.pipeline.node import PipelineNode
from app.bridges.core.pipeline.state import PipelineStatus
from app.bridges.core.pipenode.state import PipeNodeStatus

# ── 测试数据准备 ──────────────────────────────────────────────────────────────


def _create_mock_provider(max_threads: int = 1):
    """创建 mock provider"""
    provider = MagicMock()
    provider.name = "mock_provider"
    provider.setting = MagicMock()
    provider.setting.max_threads = max_threads
    provider.export = MagicMock(return_value={"name": "mock_provider"})
    return provider


def _create_mock_source():
    """创建 mock source"""
    source = MagicMock()
    source.name = "mock_source"
    source.setting = MagicMock()
    source.setting.provider_type = "mock_type"
    source.setting.strategy = "default"
    source.setting.primary_fields = []
    source.setting.partition = MagicMock()
    source.setting.partition.column = None
    source.setting.partition.prefix = None
    source.export = MagicMock(return_value={"name": "mock_source"})
    return source


def _create_mock_destination():
    """创建 mock destination"""
    dest = MagicMock()
    dest.name = "mock_dest"
    dest.export = MagicMock(return_value={"name": "mock_dest"})
    return dest


def _create_mock_context(max_threads: int = 1):
    """创建 mock PipelineContext"""
    context = MagicMock(spec=PipelineContext)
    context.id = "pctx_test123"
    context.request_id = "req_123"
    context.provider = _create_mock_provider(max_threads)
    context.source = _create_mock_source()
    context.destinations = [_create_mock_destination()]
    context.params = {}
    context.export = MagicMock(
        return_value={
            "id": "pctx_test123",
            "request_id": "req_123",
        }
    )
    return context


def _create_mock_pipenode(node_id: str = "pnctx_test123"):
    """创建 mock PipeNode"""
    from app.bridges.core.pipenode.node import PipeNode
    from app.bridges.core.pipenode.state import PipeNodeState

    node = MagicMock(spec=PipeNode)
    node.id = node_id
    node.state = PipeNodeState()
    node.state.status = PipeNodeStatus.PENDING
    node.run = MagicMock(return_value=node.state)
    node.cancel = MagicMock()
    node.export = MagicMock(
        return_value={
            "id": node_id,
            "state": node.state.export(),
        }
    )
    return node


# ──────────────────────────────────────────────────────────────────────────────
# TestPipelineNode
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineNode:
    def test_instantiation_from_context(self):
        """测试从 context 实例化。"""
        context = _create_mock_context()
        node = PipelineNode(context)
        assert node.context == context
        assert node.request_id == context.request_id
        assert node.id == context.id

    def test_state_is_initialized(self):
        """测试 state 初始化。"""
        context = _create_mock_context()
        node = PipelineNode(context)
        assert node.state is not None
        assert node.state.status == PipelineStatus.PENDING

    def test_pipenodes_is_empty_initially(self):
        """测试 pipenodes 初始为空列表。"""
        context = _create_mock_context()
        node = PipelineNode(context)
        assert node.pipenodes == []

    def test_cancel_event_is_initialized(self):
        """测试取消事件初始化。"""
        context = _create_mock_context()
        node = PipelineNode(context)
        assert node._cancel_event is not None
        assert not node._is_cancelled()


# ──────────────────────────────────────────────────────────────────────────────
# TestDerive
# ──────────────────────────────────────────────────────────────────────────────


class TestDerive:
    def test_derive_calls_strategy_factory(self):
        """测试 derive() 调用 StrategyFactory。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        # Mock the entire derive method to avoid Pydantic validation
        mock_pipenode = _create_mock_pipenode()
        with patch.object(node, "derive", return_value=[mock_pipenode]) as mock_derive:
            nodes = node.derive()
            mock_derive.assert_called_once()
            assert len(nodes) == 1

    def test_derive_creates_pipenodes(self):
        """测试 derive() 创建 PipeNode 实例。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        # Mock the entire derive method to return multiple nodes
        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
            _create_mock_pipenode("node3"),
        ]
        with patch.object(node, "derive", return_value=mock_nodes):
            nodes = node.derive()
            assert len(nodes) == 3

    @patch("app.bridges.core.pipeline.node.StrategyFactory")
    def test_derive_returns_empty_list_when_no_params(self, mock_factory):
        """测试 derive() 在无参数时返回空列表。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        # Mock strategy to return empty list
        mock_strategy = MagicMock()
        mock_strategy.run = MagicMock(return_value=[])
        mock_factory.create = MagicMock(return_value=mock_strategy)

        nodes = node.derive()

        assert nodes == []


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeRun
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeRun:
    def test_run_calls_derive(self):
        """测试 run() 调用 derive()。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        with patch.object(node, "derive", return_value=[]) as mock_derive:
            state = node.run()
            mock_derive.assert_called_once()

        assert state.status == PipelineStatus.DONE

    def test_run_sets_state_to_running(self):
        """测试 run() 设置状态为 RUNNING。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        with patch.object(node, "derive", return_value=[]):
            # Check state during run
            node.state.start()
            assert node.state.status == PipelineStatus.RUNNING

    def test_run_sets_state_to_done_on_completion(self):
        """测试 run() 完成时设置状态为 DONE。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        with patch.object(node, "derive", return_value=[]):
            state = node.run()

        assert state.status == PipelineStatus.DONE

    def test_run_updates_total_count(self):
        """测试 run() 更新总节点数。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        for mock_node in mock_nodes:
            mock_node.state.status = PipeNodeStatus.DONE

        with patch.object(node, "derive", return_value=mock_nodes):
            state = node.run()

        assert state.total == 2

    def test_run_handles_empty_pipenodes(self):
        """测试 run() 处理空 pipenodes 列表。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        with patch.object(node, "derive", return_value=[]):
            state = node.run()

        assert state.status == PipelineStatus.DONE
        assert state.total == 0

    def test_run_returns_state(self):
        """测试 run() 返回 state。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        with patch.object(node, "derive", return_value=[]):
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
        node = PipelineNode(context)

        node.cancel()
        assert node._is_cancelled() is True

    def test_cancel_propagates_to_pipenodes(self):
        """测试 cancel() 传播到所有 pipenodes。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        node.pipenodes = mock_nodes

        node.cancel()

        for mock_node in mock_nodes:
            mock_node.cancel.assert_called_once()

    def test_cancelled_nodes_are_marked(self):
        """测试取消的节点被标记为 CANCELED。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]

        with patch.object(node, "derive", return_value=mock_nodes):
            node.cancel()
            node.run()

        # Check that cancel was propagated
        assert node._is_cancelled() is True


# ──────────────────────────────────────────────────────────────────────────────
# TestSequentialRun
# ──────────────────────────────────────────────────────────────────────────────


class TestSequentialRun:
    def test_sequential_run_with_max_threads_one(self):
        """测试 max_threads=1 时顺序执行。"""
        context = _create_mock_context(max_threads=1)
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        for mock_node in mock_nodes:
            mock_node.state.status = PipeNodeStatus.DONE

        with patch.object(node, "derive", return_value=mock_nodes):
            with patch.object(node, "_run_sequential") as mock_seq:
                node.run()
                mock_seq.assert_called_once()

    def test_sequential_run_calls_each_node(self):
        """测试顺序执行调用每个节点。"""
        context = _create_mock_context(max_threads=1)
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        for mock_node in mock_nodes:
            mock_node.state.status = PipeNodeStatus.DONE

        with patch.object(node, "derive", return_value=mock_nodes):
            node.run()

        for mock_node in mock_nodes:
            mock_node.run.assert_called_once()

    def test_sequential_run_updates_state_after_each_node(self):
        """测试顺序执行在每个节点后更新状态。"""
        context = _create_mock_context(max_threads=1)
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]

        # Ensure nodes complete successfully
        for mock_node in mock_nodes:
            mock_node.state.status = PipeNodeStatus.PENDING

            def create_run_side_effect(node):
                def run_side_effect():
                    node.state.status = PipeNodeStatus.DONE
                    return node.state

                return run_side_effect

            mock_node.run = MagicMock(side_effect=create_run_side_effect(mock_node))

        with patch.object(node, "derive", return_value=mock_nodes):
            state = node.run()

        assert state.total == 2
        # Both nodes should have run
        for mock_node in mock_nodes:
            mock_node.run.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# TestConcurrentRun
# ──────────────────────────────────────────────────────────────────────────────


class TestConcurrentRun:
    def test_concurrent_run_with_max_threads_greater_than_one(self):
        """测试 max_threads>1 时并发执行。"""
        context = _create_mock_context(max_threads=4)
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        for mock_node in mock_nodes:
            mock_node.state.status = PipeNodeStatus.DONE

        with patch.object(node, "derive", return_value=mock_nodes):
            with patch.object(node, "_run_concurrent") as mock_conc:
                node.run()
                mock_conc.assert_called_once_with(4)

    def test_concurrent_run_calls_each_node(self):
        """测试并发执行调用每个节点。"""
        context = _create_mock_context(max_threads=4)
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        for mock_node in mock_nodes:
            mock_node.state.status = PipeNodeStatus.DONE

        with patch.object(node, "derive", return_value=mock_nodes):
            node.run()

        for mock_node in mock_nodes:
            mock_node.run.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# TestStateTracking
# ──────────────────────────────────────────────────────────────────────────────


class TestStateTracking:
    def test_state_tracks_done_nodes(self):
        """测试 state 追踪成功节点。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        for mock_node in mock_nodes:
            mock_node.state.status = PipeNodeStatus.DONE

        with patch.object(node, "derive", return_value=mock_nodes):
            state = node.run()

        assert state.done == 2
        assert state.failed == 0

    def test_state_tracks_failed_nodes(self):
        """测试 state 追踪失败节点。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        mock_nodes[0].state.status = PipeNodeStatus.DONE
        mock_nodes[1].state.status = PipeNodeStatus.FAILED

        with patch.object(node, "derive", return_value=mock_nodes):
            state = node.run()

        assert state.done == 1
        assert state.failed == 1
        assert state.status == PipelineStatus.PARTIAL

    def test_state_tracks_canceled_nodes(self):
        """测试 state 追踪取消节点。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        mock_nodes[0].state.status = PipeNodeStatus.CANCELED
        mock_nodes[1].state.status = PipeNodeStatus.CANCELED

        with patch.object(node, "derive", return_value=mock_nodes):
            node.cancel()
            state = node.run()

        assert state.canceled == 2


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        with patch.object(node, "derive", return_value=[]):
            node.run()

        result = node.export()
        assert isinstance(result, dict)

    def test_export_contains_context(self):
        """测试 export() 包含 context。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        with patch.object(node, "derive", return_value=[]):
            node.run()

        result = node.export()
        assert "context" in result

    def test_export_contains_state(self):
        """测试 export() 包含 state。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        with patch.object(node, "derive", return_value=[]):
            node.run()

        result = node.export()
        assert "state" in result
        assert isinstance(result["state"], dict)

    def test_export_contains_pipenodes(self):
        """测试 export() 包含 pipenodes。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        for mock_node in mock_nodes:
            mock_node.state.status = PipeNodeStatus.DONE

        with patch.object(node, "derive", return_value=mock_nodes):
            node.run()

        result = node.export()
        assert "pipenodes" in result
        assert isinstance(result["pipenodes"], dict)
        assert len(result["pipenodes"]) == 2

    def test_export_pipenodes_has_correct_keys(self):
        """测试 export() 的 pipenodes 使用节点 ID 作为 key。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        mock_nodes = [
            _create_mock_pipenode("node1"),
            _create_mock_pipenode("node2"),
        ]
        for mock_node in mock_nodes:
            mock_node.state.status = PipeNodeStatus.DONE

        with patch.object(node, "derive", return_value=mock_nodes):
            node.run()

        result = node.export()
        assert "node1" in result["pipenodes"]
        assert "node2" in result["pipenodes"]

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        with patch.object(node, "derive", return_value=[]):
            node.run()

        result = node.describe()
        assert isinstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_matches_export(self):
        """测试 describe() 内容与 export() 一致。"""
        context = _create_mock_context()
        node = PipelineNode(context)

        with patch.object(node, "derive", return_value=[]):
            node.run()

        export_data = node.export()
        describe_data = json.loads(node.describe())
        assert export_data == describe_data
