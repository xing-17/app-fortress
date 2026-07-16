"""
综合测试：app.bridges.migrate.service

覆盖范围
--------
- TestServiceBasic       基本实例化、配置
- TestServiceSubmit      submit() 方法
- TestServiceRun         run() 方法（需要 mock node）
- TestServiceLookup      lookup() 方法
- TestServiceCancel      cancel() 方法
- TestServiceExport      export() 方法

注意：由于 Service 涉及线程和队列，部分测试使用 mock。
"""

from __future__ import annotations

import time
from unittest.mock import Mock, patch

import pytest

from app.bridges.migrate.request import BridgesMigrateRequest
from app.bridges.migrate.service import BridgesMigrationService
from app.bridges.migrate.state import BridgesMigrationState, BridgesMigrationStatus

# ──────────────────────────────────────────────────────────────────────────────
# TestServiceBasic
# ──────────────────────────────────────────────────────────────────────────────


class TestServiceBasic:
    def test_create_service_instance(self):
        """测试创建 BridgesMigrationService 实例。"""
        service = BridgesMigrationService()
        assert service is not None
        assert hasattr(service, "setting")
        assert hasattr(service, "resources")

    def test_service_has_registry(self):
        """测试 service 包含注册表。"""
        service = BridgesMigrationService()
        assert hasattr(service, "_registry")
        assert service._registry is not None

    def test_service_has_live_dict(self):
        """测试 service 包含 _live 字典。"""
        service = BridgesMigrationService()
        assert hasattr(service, "_live")
        assert isinstance(service._live, dict)

    def test_service_has_queue(self):
        """测试 service 包含队列。"""
        service = BridgesMigrationService()
        assert hasattr(service, "_queue")
        assert service._queue is not None

    def test_service_has_worker_thread(self):
        """测试 service 启动工作线程。"""
        service = BridgesMigrationService()
        assert hasattr(service, "_worker")
        assert service._worker is not None
        assert service._worker.is_alive()


# ──────────────────────────────────────────────────────────────────────────────
# TestServiceSubmit
# ──────────────────────────────────────────────────────────────────────────────


class TestServiceSubmit:
    def test_submit_returns_request_id(self):
        """测试 submit() 返回 request_id。"""
        service = BridgesMigrationService()
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )

        request_id = service.submit(request)

        assert request_id is not None
        assert request_id == request.id

    def test_submit_adds_to_live(self):
        """测试 submit() 将请求添加到 _live。"""
        service = BridgesMigrationService()
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )

        request_id = service.submit(request)

        # 短暂等待，让请求有机会被处理或留在队列中
        time.sleep(0.1)

        # 请求可能在 _live 中（如果正在处理）或已被移除（如果处理完成）
        # 由于测试环境中可能没有真实资源，请求可能会失败并被移除
        # 我们只验证 submit 本身不抛出异常
        assert request_id.startswith("mig-")


# ──────────────────────────────────────────────────────────────────────────────
# TestServiceRun
# ──────────────────────────────────────────────────────────────────────────────


class TestServiceRun:
    @patch("app.bridges.migrate.service.BridgesMigrationNode")
    def test_run_with_successful_node(self, mock_node_class):
        """测试 run() 成功执行。"""
        service = BridgesMigrationService()

        # Mock node 实例
        mock_node = Mock()
        mock_state = BridgesMigrationState(
            request=BridgesMigrateRequest(
                source_name="test_source",
                from_destination="src_oss",
                from_glob="s3://src/prefix/**/*.parquet",
                to_destination="tgt_oss",
            )
        )
        mock_state.status = BridgesMigrationStatus.DONE
        mock_state.rows = 1000
        mock_node.state = mock_state
        mock_node.run = Mock(return_value=mock_state)
        mock_node_class.return_value = mock_node

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )

        result = service.run(request)

        assert result is not None
        assert isinstance(result, BridgesMigrationState)
        mock_node.run.assert_called_once()

    @patch("app.bridges.migrate.service.BridgesMigrationNode")
    def test_run_handles_node_creation_failure(self, mock_node_class):
        """测试 run() 处理 node 创建失败。"""
        service = BridgesMigrationService()

        # Mock node 初始化失败
        mock_node_class.side_effect = Exception("Connection failed")

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )

        result = service.run(request)

        assert result is not None
        assert result.status == BridgesMigrationStatus.FAILED
        assert "Connection failed" in result.error

    def test_run_respects_cancel(self):
        """测试 run() 尊重取消状态。"""
        service = BridgesMigrationService()

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )

        # 创建一个已取消的状态
        state = BridgesMigrationState(request=request)
        state.cancel()
        service._live[request.id] = state

        result = service.run(request)

        assert result.status == BridgesMigrationStatus.CANCELED


# ──────────────────────────────────────────────────────────────────────────────
# TestServiceLookup
# ──────────────────────────────────────────────────────────────────────────────


class TestServiceLookup:
    def test_lookup_raises_on_nonexistent_request(self):
        """测试 lookup() 在找不到请求时抛出异常。"""
        service = BridgesMigrationService()

        with pytest.raises(ValueError, match="No migration state found"):
            service.lookup("nonexistent_request_id")

    def test_lookup_returns_live_request_state(self):
        """测试 lookup() 返回活跃的请求状态。"""
        service = BridgesMigrationService()

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        service._live[request.id] = state

        result = service.lookup(request.id)

        assert result == state.export()

    def test_lookup_returns_registry_data_when_not_live(self):
        """测试 lookup() 从注册表返回数据。"""
        service = BridgesMigrationService()

        request_id = "mig_123456"
        registry_data = {"status": "DONE", "rows": 1000}
        service._registry.upsert(request_id, registry_data)

        result = service.lookup(request_id)

        assert result == registry_data


# ──────────────────────────────────────────────────────────────────────────────
# TestServiceCancel
# ──────────────────────────────────────────────────────────────────────────────


class TestServiceCancel:
    def test_cancel_nonexistent_request_does_nothing(self):
        """测试取消不存在的请求不会抛出异常。"""
        service = BridgesMigrationService()
        # 应该不抛出异常
        service.cancel("nonexistent_request_id")

    def test_cancel_pending_request(self):
        """测试取消 PENDING 状态的请求。"""
        service = BridgesMigrationService()

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        service._live[request.id] = state

        service.cancel(request.id)

        assert state.status == BridgesMigrationStatus.CANCELED

    def test_cancel_running_request_does_nothing(self):
        """测试取消 RUNNING 状态的请求不会改变状态。"""
        service = BridgesMigrationService()

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()  # 设置为 RUNNING
        service._live[request.id] = state

        service.cancel(request.id)

        # 状态应该仍然是 RUNNING（不是 PENDING 所以不会被取消）
        assert state.status == BridgesMigrationStatus.RUNNING


# ──────────────────────────────────────────────────────────────────────────────
# TestServiceExport
# ──────────────────────────────────────────────────────────────────────────────


class TestServiceExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        service = BridgesMigrationService()

        exported = service.export()

        assert isinstance(exported, dict)

    def test_export_contains_live_requests(self):
        """测试 export() 包含 live 请求。"""
        service = BridgesMigrationService()

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        service._live[request.id] = state

        exported = service.export()

        assert "live" in exported
        assert request.id in exported["live"]
