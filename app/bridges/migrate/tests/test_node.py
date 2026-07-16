"""
综合测试：app.bridges.migrate.node

覆盖范围
--------
- TestNodeBasic          基本实例化、属性验证（需要大量 mock）
- TestNodePlan           plan() 方法生成 SQL 语句
- TestNodeExport         export() 和 describe() 方法

注意：由于 Node 涉及 DuckDB 和资源连接，测试使用大量 mock。
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

from app.bridges.migrate.node import BridgesMigrationNode
from app.bridges.migrate.request import BridgesMigrateRequest
from app.bridges.migrate.state import BridgesMigrationState

# ──────────────────────────────────────────────────────────────────────────────
# TestNodeBasic
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeBasic:
    @patch("app.bridges.migrate.node.ModuleBridgesWarehouse")
    @patch("app.bridges.migrate.node.duckdb.connect")
    def test_create_node_instance(self, mock_duckdb, mock_warehouse):
        """测试创建 BridgesMigrationNode 实例。"""
        # Mock 资源
        mock_source = Mock()
        mock_from_dest = Mock()
        mock_from_dest.connection = Mock()
        mock_from_dest.connection.ingest_to_duckdb = Mock(return_value=("src_secret", mock_duckdb.return_value))

        mock_to_dest = Mock()
        mock_to_dest.connection = Mock()
        mock_to_dest.connection.ingest_to_duckdb = Mock(return_value=("tgt_secret", mock_duckdb.return_value))
        mock_to_dest.get_duckdb_base_uri = Mock(return_value="s3://target-bucket")

        mock_warehouse.get_source = Mock(return_value=mock_source)
        mock_warehouse.get_destination = Mock(side_effect=[mock_from_dest, mock_to_dest])

        # Mock DuckDB execute
        mock_client = Mock()
        mock_client.execute = Mock(return_value=Mock(fetchone=Mock(return_value=[True])))
        mock_duckdb.return_value = mock_client

        # 创建 setting mock
        mock_setting = Mock()
        mock_setting.extensions = ["httpfs"]
        mock_setting.memory_limit = "1GB"
        mock_setting.temp_directory = "/tmp"
        mock_setting.max_workers = 4

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )

        node = BridgesMigrationNode(
            setting=mock_setting,
            request=request,
        )

        assert node is not None
        assert node.id == request.id
        assert isinstance(node.state, BridgesMigrationState)

    @patch("app.bridges.migrate.node.ModuleBridgesWarehouse")
    @patch("app.bridges.migrate.node.duckdb.connect")
    def test_node_has_required_attributes(self, mock_duckdb, mock_warehouse):
        """测试节点包含必要的属性。"""
        # Mock 资源
        mock_source = Mock()
        mock_from_dest = Mock()
        mock_from_dest.connection = Mock()
        mock_from_dest.connection.ingest_to_duckdb = Mock(return_value=("src_secret", mock_duckdb.return_value))

        mock_to_dest = Mock()
        mock_to_dest.connection = Mock()
        mock_to_dest.connection.ingest_to_duckdb = Mock(return_value=("tgt_secret", mock_duckdb.return_value))
        mock_to_dest.get_duckdb_base_uri = Mock(return_value="s3://target-bucket")

        mock_warehouse.get_source = Mock(return_value=mock_source)
        mock_warehouse.get_destination = Mock(side_effect=[mock_from_dest, mock_to_dest])

        mock_client = Mock()
        mock_client.execute = Mock(return_value=Mock(fetchone=Mock(return_value=[True])))
        mock_duckdb.return_value = mock_client

        mock_setting = Mock()
        mock_setting.extensions = ["httpfs"]
        mock_setting.memory_limit = "1GB"
        mock_setting.temp_directory = "/tmp"
        mock_setting.max_workers = 4

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )

        node = BridgesMigrationNode(
            setting=mock_setting,
            request=request,
        )

        assert hasattr(node, "id")
        assert hasattr(node, "state")
        assert hasattr(node, "from_glob")
        assert hasattr(node, "to_glob")
        assert hasattr(node, "transform_sql")
        assert hasattr(node, "options")


# ──────────────────────────────────────────────────────────────────────────────
# TestNodePlan
# ──────────────────────────────────────────────────────────────────────────────


class TestNodePlan:
    @patch("app.bridges.migrate.node.ModuleBridgesWarehouse")
    @patch("app.bridges.migrate.node.duckdb.connect")
    def test_plan_generates_sql_statement(self, mock_duckdb, mock_warehouse):
        """测试 plan() 生成正确的 SQL 语句。"""
        # Mock 资源
        mock_source = Mock()
        mock_from_dest = Mock()
        mock_from_dest.connection = Mock()
        mock_from_dest.connection.ingest_to_duckdb = Mock(return_value=("src_secret", mock_duckdb.return_value))

        mock_to_dest = Mock()
        mock_to_dest.connection = Mock()
        mock_to_dest.connection.ingest_to_duckdb = Mock(return_value=("tgt_secret", mock_duckdb.return_value))
        mock_to_dest.get_duckdb_base_uri = Mock(return_value="s3://target-bucket")

        mock_warehouse.get_source = Mock(return_value=mock_source)
        mock_warehouse.get_destination = Mock(side_effect=[mock_from_dest, mock_to_dest])

        mock_client = Mock()
        mock_client.execute = Mock(return_value=Mock(fetchone=Mock(return_value=[True])))
        mock_duckdb.return_value = mock_client

        mock_setting = Mock()
        mock_setting.extensions = ["httpfs"]
        mock_setting.memory_limit = "1GB"
        mock_setting.temp_directory = "/tmp"
        mock_setting.max_workers = 4

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )

        node = BridgesMigrationNode(
            setting=mock_setting,
            request=request,
        )

        plan = node.plan()

        assert isinstance(plan, str)
        assert "COPY" in plan
        assert "TO" in plan
        assert node.to_glob in plan

    @patch("app.bridges.migrate.node.ModuleBridgesWarehouse")
    @patch("app.bridges.migrate.node.duckdb.connect")
    def test_plan_includes_transform_sql(self, mock_duckdb, mock_warehouse):
        """测试 plan() 包含 transform_sql。"""
        mock_source = Mock()
        mock_from_dest = Mock()
        mock_from_dest.connection = Mock()
        mock_from_dest.connection.ingest_to_duckdb = Mock(return_value=("src_secret", mock_duckdb.return_value))

        mock_to_dest = Mock()
        mock_to_dest.connection = Mock()
        mock_to_dest.connection.ingest_to_duckdb = Mock(return_value=("tgt_secret", mock_duckdb.return_value))
        mock_to_dest.get_duckdb_base_uri = Mock(return_value="s3://target-bucket")

        mock_warehouse.get_source = Mock(return_value=mock_source)
        mock_warehouse.get_destination = Mock(side_effect=[mock_from_dest, mock_to_dest])

        mock_client = Mock()
        mock_client.execute = Mock(return_value=Mock(fetchone=Mock(return_value=[True])))
        mock_duckdb.return_value = mock_client

        mock_setting = Mock()
        mock_setting.extensions = ["httpfs"]
        mock_setting.memory_limit = "1GB"
        mock_setting.temp_directory = "/tmp"
        mock_setting.max_workers = 4

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
            transform_sql="SELECT * EXCLUDE(col1) FROM <source>",
        )

        node = BridgesMigrationNode(
            setting=mock_setting,
            request=request,
        )

        plan = node.plan()

        # 验证 transform_sql 被应用（<source> 应该被替换）
        assert "<source>" not in plan
        assert "read_parquet" in plan
        assert "EXCLUDE(col1)" in plan


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeExport
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeExport:
    @patch("app.bridges.migrate.node.ModuleBridgesWarehouse")
    @patch("app.bridges.migrate.node.duckdb.connect")
    def test_export_returns_dict(self, mock_duckdb, mock_warehouse):
        """测试 export() 返回字典。"""
        mock_source = Mock()
        mock_from_dest = Mock()
        mock_from_dest.connection = Mock()
        mock_from_dest.connection.ingest_to_duckdb = Mock(return_value=("src_secret", mock_duckdb.return_value))

        mock_to_dest = Mock()
        mock_to_dest.connection = Mock()
        mock_to_dest.connection.ingest_to_duckdb = Mock(return_value=("tgt_secret", mock_duckdb.return_value))
        mock_to_dest.get_duckdb_base_uri = Mock(return_value="s3://target-bucket")

        mock_warehouse.get_source = Mock(return_value=mock_source)
        mock_warehouse.get_destination = Mock(side_effect=[mock_from_dest, mock_to_dest])

        mock_client = Mock()
        mock_client.execute = Mock(return_value=Mock(fetchone=Mock(return_value=[True])))
        mock_duckdb.return_value = mock_client

        mock_setting = Mock()
        mock_setting.extensions = ["httpfs"]
        mock_setting.memory_limit = "1GB"
        mock_setting.temp_directory = "/tmp"
        mock_setting.max_workers = 4

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )

        node = BridgesMigrationNode(
            setting=mock_setting,
            request=request,
        )

        exported = node.export()

        assert isinstance(exported, dict)
        assert "id" in exported
        assert "request" in exported
        assert "state" in exported

    @patch("app.bridges.migrate.node.ModuleBridgesWarehouse")
    @patch("app.bridges.migrate.node.duckdb.connect")
    def test_describe_returns_json_string(self, mock_duckdb, mock_warehouse):
        """测试 describe() 返回 JSON 字符串。"""
        mock_source = Mock()
        mock_from_dest = Mock()
        mock_from_dest.connection = Mock()
        mock_from_dest.connection.ingest_to_duckdb = Mock(return_value=("src_secret", mock_duckdb.return_value))

        mock_to_dest = Mock()
        mock_to_dest.connection = Mock()
        mock_to_dest.connection.ingest_to_duckdb = Mock(return_value=("tgt_secret", mock_duckdb.return_value))
        mock_to_dest.get_duckdb_base_uri = Mock(return_value="s3://target-bucket")

        mock_warehouse.get_source = Mock(return_value=mock_source)
        mock_warehouse.get_destination = Mock(side_effect=[mock_from_dest, mock_to_dest])

        mock_client = Mock()
        mock_client.execute = Mock(return_value=Mock(fetchone=Mock(return_value=[True])))
        mock_duckdb.return_value = mock_client

        mock_setting = Mock()
        mock_setting.extensions = ["httpfs"]
        mock_setting.memory_limit = "1GB"
        mock_setting.temp_directory = "/tmp"
        mock_setting.max_workers = 4

        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://src/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )

        node = BridgesMigrationNode(
            setting=mock_setting,
            request=request,
        )

        described = node.describe()

        assert isinstance(described, str)
        # 验证是否为有效的 JSON
        parsed = json.loads(described)
        assert isinstance(parsed, dict)
