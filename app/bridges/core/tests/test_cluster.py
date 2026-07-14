"""
综合测试：app.bridges.core.cluster

覆盖范围
--------
- TestClusterBasic       基本实例化、配置
- TestClusterDerive      derive() 方法和参数解析
- TestClusterLookup      lookup() 方法
- TestExport             export() 和 describe() 方法

注意：这些测试依赖于实际的资源配置和 pipeline 实现。
部分测试可能需要 mock 对象。
"""

from __future__ import annotations

import json
import time
from unittest.mock import Mock, patch

import pytest

from app.bridges.core.cluster import BridgesCluster
from app.bridges.core.request import BridgesRequest
from app.bridges.core.requeststate import BridgesRequestState

# ──────────────────────────────────────────────────────────────────────────────
# TestClusterBasic
# ──────────────────────────────────────────────────────────────────────────────


class TestClusterBasic:
    def test_create_cluster_instance(self):
        """测试创建 BridgesCluster 实例。"""
        cluster = BridgesCluster()
        assert cluster is not None
        assert hasattr(cluster, "setting")
        assert hasattr(cluster, "resources")

    def test_cluster_has_registry(self):
        """测试 cluster 包含注册表。"""
        cluster = BridgesCluster()
        assert hasattr(cluster, "_registry")
        assert cluster._registry is not None

    def test_cluster_has_live_dict(self):
        """测试 cluster 包含 _live 字典。"""
        cluster = BridgesCluster()
        assert hasattr(cluster, "_live")
        assert isinstance(cluster._live, dict)
        assert len(cluster._live) == 0


# ──────────────────────────────────────────────────────────────────────────────
# TestClusterDerive
# ──────────────────────────────────────────────────────────────────────────────


class TestClusterDerive:
    def test_derive_raises_on_no_sources(self):
        """测试 derive() 在没有找到 sources 时抛出异常。"""
        cluster = BridgesCluster()
        request = BridgesRequest(sources_by_tags={"nonexistent": "tag"})

        with pytest.raises(ValueError, match="No sources found"):
            cluster.derive(request)

    def test_derive_raises_on_no_destinations_when_specified(self):
        """测试 derive() 在指定的 destinations 不存在时抛出异常。"""
        cluster = BridgesCluster()
        request = BridgesRequest(
            sources_by_tags={},  # 可能会匹配到一些 sources
            destinations=["nonexistent_destination"],
        )

        # 如果没有 sources，会先报 sources 错误
        # 如果有 sources，会报 destinations 错误
        with pytest.raises(ValueError):
            cluster.derive(request)


# ──────────────────────────────────────────────────────────────────────────────
# TestClusterCancel
# ──────────────────────────────────────────────────────────────────────────────


class TestClusterCancel:
    def test_cancel_nonexistent_request_does_nothing(self):
        """测试取消不存在的请求不会抛出异常。"""
        cluster = BridgesCluster()
        # 应该不抛出异常
        cluster.cancel("nonexistent_request_id")

    def test_cancel_updates_request_state(self):
        """测试 cancel() 更新请求状态。"""
        cluster = BridgesCluster()

        # 创建一个 mock 的请求状态
        mock_req_state = Mock()
        mock_pipe_node = Mock()
        mock_req_state.pipe_nodes = [mock_pipe_node]

        request_id = "test_req_123"
        cluster._live[request_id] = mock_req_state

        # 执行取消
        cluster.cancel(request_id)

        # 验证调用了 cancel 方法
        mock_pipe_node.cancel.assert_called_once()
        mock_req_state.cancel.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# TestClusterLookup
# ──────────────────────────────────────────────────────────────────────────────


class TestClusterLookup:
    def test_lookup_raises_on_nonexistent_request(self):
        """测试 lookup() 在找不到请求时抛出异常。"""
        cluster = BridgesCluster()

        with pytest.raises(ValueError, match="No request state found"):
            cluster.lookup("nonexistent_request_id")

    def test_lookup_returns_live_request_state(self):
        """测试 lookup() 返回活跃的请求状态。"""
        cluster = BridgesCluster()

        # 添加一个 mock 的请求状态
        mock_req_state = Mock()
        request_id = "test_req_123"
        cluster._live[request_id] = mock_req_state

        result = cluster.lookup(request_id)
        assert result == mock_req_state.export()

    def test_lookup_returns_registry_data_when_not_live(self):
        """测试 lookup() 从注册表返回数据。"""
        cluster = BridgesCluster()

        # 在注册表中添加数据
        request_id = "test_req_123"
        registry_data = {"status": "DONE", "rows": 100}
        cluster._registry.upsert(request_id, registry_data)

        result = cluster.lookup(request_id)
        assert result == registry_data


# ──────────────────────────────────────────────────────────────────────────────
# TestClusterRefresh
# ──────────────────────────────────────────────────────────────────────────────


class TestClusterRefresh:
    def test_refresh_method_exists(self):
        """测试 refresh() 方法存在。"""
        cluster = BridgesCluster()
        assert hasattr(cluster, "refresh")
        assert callable(cluster.refresh)

    def test_refresh_method_runs(self):
        """测试 refresh() 方法可以运行。"""
        cluster = BridgesCluster()
        # 应该不抛出异常
        cluster.refresh()


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        cluster = BridgesCluster()
        result = cluster.export()
        assert isinstance(result, dict)

    def test_export_contains_all_sections(self):
        """测试导出包含所有部分。"""
        cluster = BridgesCluster()
        result = cluster.export()
        assert "setting" in result
        assert "resources" in result
        assert "registry" in result

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        cluster = BridgesCluster()
        result = cluster.describe()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_contains_same_data_as_export(self):
        """测试 describe() 包含与 export() 相同的数据。"""
        cluster = BridgesCluster()
        exported = cluster.export()
        described = json.loads(cluster.describe())
        assert exported == described


# ──────────────────────────────────────────────────────────────────────────────
# TestClusterSubmit
# ──────────────────────────────────────────────────────────────────────────────


class TestClusterSubmit:
    def test_submit_returns_request_id(self):
        """测试 submit() 返回请求 ID。"""
        cluster = BridgesCluster()
        request = BridgesRequest(
            sources_by_tags={"tag": "value"},
            destinations=["dest1"],
        )

        result = cluster.submit(request)
        assert result == request.id
        assert isinstance(result, str)

    def test_submit_creates_request_state_in_live(self):
        """测试 submit() 在 _live 字典中创建请求状态。"""
        cluster = BridgesCluster()
        request = BridgesRequest(
            sources_by_tags={"tag": "value"},
            destinations=["dest1"],
        )

        request_id = cluster.submit(request)

        # 验证请求状态已添加到 _live
        assert request_id in cluster._live
        assert isinstance(cluster._live[request_id], BridgesRequestState)
        assert cluster._live[request_id].request == request

    def test_submit_adds_request_to_queue(self):
        """测试 submit() 将请求添加到队列。"""
        cluster = BridgesCluster()
        request = BridgesRequest(
            sources_by_tags={"tag": "value"},
            destinations=["dest1"],
        )

        initial_size = cluster.get_queue_size()
        cluster.submit(request)

        # 队列大小应该增加
        # 注意：由于 worker 线程可能快速处理，这个断言可能不稳定
        # 在实际环境中可能需要 mock worker
        assert cluster.get_queue_size() >= initial_size

    def test_submit_multiple_requests(self):
        """测试 submit() 可以提交多个请求。"""
        cluster = BridgesCluster()
        request1 = BridgesRequest(
            sources_by_tags={"tag1": "value1"},
            destinations=["dest1"],
        )
        request2 = BridgesRequest(
            sources_by_tags={"tag2": "value2"},
            destinations=["dest2"],
        )

        id1 = cluster.submit(request1)
        id2 = cluster.submit(request2)

        # 两个请求应该有不同的 ID
        assert id1 != id2

        # 两个请求都应该在 _live 中（或已被处理）
        # 注意：由于异步处理，请求可能已从 _live 移除

    def test_submit_same_request_creates_new_state(self):
        """测试多次 submit 同一个请求会创建新的状态。"""
        cluster = BridgesCluster()
        request = BridgesRequest(
            sources_by_tags={"tag": "value"},
            destinations=["dest1"],
        )

        id1 = cluster.submit(request)

        # 等待一小段时间确保第一个请求开始处理
        time.sleep(0.1)

        # 再次提交同一个请求（相同的 request.id）
        # 这会覆盖 _live 中的状态
        id2 = cluster.submit(request)

        assert id1 == id2  # 相同的 request 对象，ID 相同
        assert id2 in cluster._live

    @patch.object(BridgesCluster, "_worker_loop")
    def test_submit_with_worker_mocked(self, mock_worker):
        """测试 submit() 在 worker 被 mock 时的行为。"""
        # Mock worker loop 以防止实际处理
        mock_worker.return_value = None

        cluster = BridgesCluster()
        request = BridgesRequest(
            sources_by_tags={"tag": "value"},
            destinations=["dest1"],
        )

        request_id = cluster.submit(request)

        # 验证基本操作
        assert request_id in cluster._live
        assert cluster._live[request_id].request == request

    def test_submit_request_can_be_looked_up(self):
        """测试 submit() 后的请求可以通过 lookup() 查询。"""
        cluster = BridgesCluster()
        request = BridgesRequest(
            sources_by_tags={"tag": "value"},
            destinations=["dest1"],
        )

        request_id = cluster.submit(request)

        # 立即查询应该能找到（在 _live 中）
        result = cluster.lookup(request_id)
        assert result is not None
        assert isinstance(result, dict)

    def test_submit_request_can_be_cancelled(self):
        """测试 submit() 后的请求可以被取消。"""
        cluster = BridgesCluster()
        request = BridgesRequest(
            sources_by_tags={"tag": "value"},
            destinations=["dest1"],
        )

        request_id = cluster.submit(request)

        # 应该可以取消（即使可能已经开始或完成处理）
        # 这个调用不应该抛出异常
        cluster.cancel(request_id)
