"""
综合测试：app.bridges.migrate.node.node

覆盖范围
--------
- TestMigrateNode          实例化、属性访问
- TestNodeSetup            setup() 方法和初始化流程
- TestNodeRun              run() 方法的基本流程
- TestNodeCancel           cancel() 取消功能
- TestNodeState            状态更新和追踪
- TestTransformSQL         SQL 转换处理
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from app.bridges.migrate.node.context import MigrateNodeContext
from app.bridges.migrate.node.node import MigrateNode
from app.bridges.migrate.node.state import MigrateNodeStatus

# ── 测试数据准备 ──────────────────────────────────────────────────────────────


def _create_mock_destination(name: str = "mock_dest"):
    """创建符合 BaseDestination 接口的 mock 对象"""
    from app.bridges.resources.destinations.base.destination import BaseDestination

    dest = Mock(spec=BaseDestination)
    dest.name = name

    # Mock connection
    connection = MagicMock()
    connection.name = f"{name}_connection"

    # Mock DuckDB secret
    secret = MagicMock()
    secret.name = f"{name}_secret"
    secret.create = MagicMock()
    secret.check = MagicMock()
    connection.get_duckdb_secret = MagicMock(return_value=secret)

    dest.connection = connection

    return dest


def _create_mock_context():
    """创建用于测试的 MigrateNodeContext"""
    context = MagicMock(spec=MigrateNodeContext)
    context.id = "mignctx_test123"
    context.identifier = "test_source::mignctx_test123"
    context.request_id = "req_123"
    context.source_name = "test_source"
    context.from_destination = _create_mock_destination("from_dest")
    context.from_glob = "s3://bucket/from/**/*.parquet"
    context.to_destination = _create_mock_destination("to_dest")
    context.to_glob = "s3://bucket/to/**/*.parquet"
    context.transform_sql = None
    context.options = []
    context.extensions = []

    return context


# ──────────────────────────────────────────────────────────────────────────────
# TestMigrateNode
# ──────────────────────────────────────────────────────────────────────────────


class TestMigrateNode:
    def test_instantiation_from_context(self):
        """测试从 context 实例化。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert node.context == context
        assert node.id == context.id
        assert node.identifier == context.identifier

    def test_state_is_initialized(self):
        """测试 state 初始化。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert node.state is not None
        assert node.state.status == MigrateNodeStatus.PENDING

    def test_request_id_accessible(self):
        """测试 request_id 可访问。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert node.request_id == "req_123"

    def test_from_destination_accessible(self):
        """测试 from_destination 可访问。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert node._from_dest.name == "from_dest"

    def test_to_destination_accessible(self):
        """测试 to_destination 可访问。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert node._to_dest.name == "to_dest"

    def test_from_glob_accessible(self):
        """测试 from_glob 可访问。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert node._from_glob == "s3://bucket/from/**/*.parquet"

    def test_to_glob_accessible(self):
        """测试 to_glob 可访问。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert node._to_glob == "s3://bucket/to/**/*.parquet"


# ──────────────────────────────────────────────────────────────────────────────
# TestTransformSQL
# ──────────────────────────────────────────────────────────────────────────────


class TestTransformSQL:
    def test_default_transform_sql_when_not_provided(self):
        """测试未提供时默认 transform_sql。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        expected = "SELECT * FROM read_parquet('s3://bucket/from/**/*.parquet', hive_partitioning = true)"
        assert node.transform_sql == expected

    def test_transform_sql_replaces_source_placeholder(self):
        """测试 transform_sql 替换 <source> 占位符。"""
        context = _create_mock_context()
        context.transform_sql = "SELECT id, name FROM <source> WHERE date > '2024-01-01'"
        node = MigrateNode(context)
        assert "<source>" not in node.transform_sql
        assert "read_parquet" in node.transform_sql
        assert "s3://bucket/from/**/*.parquet" in node.transform_sql

    def test_transform_sql_raises_error_without_source_placeholder(self):
        """测试 transform_sql 没有 <source> 占位符时抛出错误。"""
        context = _create_mock_context()
        context.transform_sql = "SELECT * FROM some_table"
        try:
            _ = MigrateNode(context)
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "must contain '<source>'" in str(e)


# ──────────────────────────────────────────────────────────────────────────────
# TestOptions
# ──────────────────────────────────────────────────────────────────────────────


class TestOptions:
    def test_default_options_when_not_provided(self):
        """测试未提供时默认 options。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert "FORMAT parquet" in node.options
        assert "COMPRESSION snappy" in node.options

    def test_custom_options_when_provided(self):
        """测试提供自定义 options。"""
        context = _create_mock_context()
        context.options = ["FORMAT csv", "DELIMITER ','"]
        node = MigrateNode(context)
        assert "FORMAT csv" in node.options
        assert "DELIMITER ','" in node.options


# ──────────────────────────────────────────────────────────────────────────────
# TestExtensions
# ──────────────────────────────────────────────────────────────────────────────


class TestExtensions:
    def test_default_extensions_when_not_provided(self):
        """测试未提供时默认 extensions。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert "httpfs" in node.extensions

    def test_custom_extensions_when_provided(self):
        """测试提供自定义 extensions。"""
        context = _create_mock_context()
        context.extensions = ["httpfs", "parquet", "json"]
        node = MigrateNode(context)
        assert "httpfs" in node.extensions
        assert "parquet" in node.extensions
        assert "json" in node.extensions


# ──────────────────────────────────────────────────────────────────────────────
# TestScript
# ──────────────────────────────────────────────────────────────────────────────


class TestScript:
    def test_script_is_generated(self):
        """测试 script 自动生成。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert node.script is not None
        assert isinstance(node.script, str)

    def test_script_contains_copy_statement(self):
        """测试 script 包含 COPY 语句。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert "COPY" in node.script

    def test_script_contains_to_glob(self):
        """测试 script 包含目标路径。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        assert "s3://bucket/to/**/*.parquet" in node.script

    def test_script_contains_transform_sql(self):
        """测试 script 包含 transform_sql。"""
        context = _create_mock_context()
        context.transform_sql = "SELECT id, name FROM <source>"
        node = MigrateNode(context)
        assert "SELECT id, name FROM" in node.script
        assert "read_parquet" in node.script


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeSetup
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeSetup:
    def test_setup_initializes_client(self):
        """测试 setup() 初始化客户端。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        with patch.object(node, "_setup_client") as mock_setup_client:
            with patch.object(node, "_setup_from_secret"):
                with patch.object(node, "_setup_to_secret"):
                    node.setup()
        mock_setup_client.assert_called_once()

    def test_setup_creates_from_secret(self):
        """测试 setup() 创建 from secret。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        with patch.object(node, "_setup_client"):
            with patch.object(node, "_setup_from_secret") as mock_from_secret:
                with patch.object(node, "_setup_to_secret"):
                    node.setup()
        mock_from_secret.assert_called_once()

    def test_setup_creates_to_secret(self):
        """测试 setup() 创建 to secret。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        with patch.object(node, "_setup_client"):
            with patch.object(node, "_setup_from_secret"):
                with patch.object(node, "_setup_to_secret") as mock_to_secret:
                    node.setup()
        mock_to_secret.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeRun
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeRun:
    def test_run_calls_setup(self):
        """测试 run() 调用 setup()。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (100,)
        mock_client.execute.return_value = mock_result
        node._client = mock_client

        with patch.object(node, "setup") as mock_setup:
            _ = node.run()
        mock_setup.assert_called_once()

    def test_run_executes_script(self):
        """测试 run() 执行 script。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (100,)
        mock_client.execute.return_value = mock_result
        node._client = mock_client

        with patch.object(node, "setup"):
            _ = node.run()
        mock_client.execute.assert_called_once_with(node.script)

    def test_run_sets_state_to_done_on_success(self):
        """测试 run() 成功时设置状态为 DONE。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (100,)
        mock_client.execute.return_value = mock_result
        node._client = mock_client

        with patch.object(node, "setup"):
            state = node.run()
        assert state.status == MigrateNodeStatus.DONE
        assert state.succeeded is True

    def test_run_sets_rows_on_success(self):
        """测试 run() 成功时设置行数。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (250,)
        mock_client.execute.return_value = mock_result
        node._client = mock_client

        with patch.object(node, "setup"):
            state = node.run()
        assert state.rows == 250

    def test_run_sets_state_to_failed_on_exception(self):
        """测试 run() 异常时设置状态为 FAILED。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        mock_client.execute.side_effect = Exception("Test error")
        node._client = mock_client

        with patch.object(node, "setup"):
            state = node.run()
        assert state.status == MigrateNodeStatus.FAILED
        assert "Test error" in state.error

    def test_run_returns_state(self):
        """测试 run() 返回 state。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (100,)
        mock_client.execute.return_value = mock_result
        node._client = mock_client

        with patch.object(node, "setup"):
            state = node.run()
        assert state is not None
        assert state == node.state

    def test_run_closes_client(self):
        """测试 run() 关闭客户端。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (100,)
        mock_client.execute.return_value = mock_result
        node._client = mock_client

        with patch.object(node, "setup"):
            _ = node.run()
        mock_client.close.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeCancel
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeCancel:
    def test_cancel_sets_event(self):
        """测试 cancel() 设置取消事件。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        node.cancel()
        assert node._cancel_event.is_set() is True

    def test_cancel_interrupts_client(self):
        """测试 cancel() 中断客户端。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        node._client = mock_client

        node.cancel()
        mock_client.interrupt.assert_called_once()

    def test_run_checks_cancellation_before_execution(self):
        """测试 run() 在执行前检查取消状态。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        node.cancel()
        state = node.run()
        assert state.status == MigrateNodeStatus.CANCELED

    def test_cancelled_run_does_not_call_setup(self):
        """测试取消的 run() 不调用 setup()。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        node.cancel()
        with patch.object(node, "setup") as mock_setup:
            _ = node.run()
        mock_setup.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# TestNodeState
# ──────────────────────────────────────────────────────────────────────────────


class TestNodeState:
    def test_state_tracks_started_at(self):
        """测试 state 追踪开始时间。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (100,)
        mock_client.execute.return_value = mock_result
        node._client = mock_client

        with patch.object(node, "setup"):
            state = node.run()
        assert state.started_at is not None

    def test_state_tracks_finished_at(self):
        """测试 state 追踪结束时间。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (100,)
        mock_client.execute.return_value = mock_result
        node._client = mock_client

        with patch.object(node, "setup"):
            state = node.run()
        assert state.finished_at is not None

    def test_state_calculates_duration(self):
        """测试 state 计算执行时长。"""
        context = _create_mock_context()
        node = MigrateNode(context)

        # Mock the entire _client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (100,)
        mock_client.execute.return_value = mock_result
        node._client = mock_client

        with patch.object(node, "setup"):
            state = node.run()
        assert state.duration_seconds is not None
        assert state.duration_seconds >= 0


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        result = node.export()
        assert isinstance(result, dict)

    def test_export_contains_context(self):
        """测试 export() 包含 context。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        result = node.export()
        assert "context" in result

    def test_export_contains_state(self):
        """测试 export() 包含 state。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        result = node.export()
        assert "state" in result

    def test_export_contains_script(self):
        """测试 export() 包含 script。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        result = node.export()
        assert "script" in result

    def test_export_contains_extensions(self):
        """测试 export() 包含 extensions。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        result = node.export()
        assert "extensions" in result

    def test_export_contains_options(self):
        """测试 export() 包含 options。"""
        context = _create_mock_context()
        node = MigrateNode(context)
        result = node.export()
        assert "options" in result

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        # Create a real context instead of mock to avoid JSON serialization issues
        real_context = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination("from_dest"),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination("to_dest"),
            to_glob="s3://bucket/to/**/*.parquet",
        )
        node = MigrateNode(real_context)
        result = node.describe()
        assert isinstance(result, str)
        import json

        parsed = json.loads(result)
        assert isinstance(parsed, dict)
