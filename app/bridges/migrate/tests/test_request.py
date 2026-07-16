"""
综合测试：app.bridges.migrate.request

覆盖范围
--------
- TestBridgesMigrateRequest  基本实例化、字段验证
- TestRequestID              ID 生成和前缀验证
- TestRequestExport          export() 方法
"""

from __future__ import annotations

from app.bridges.migrate.request import BridgesMigrateRequest

# ──────────────────────────────────────────────────────────────────────────────
# TestBridgesMigrateRequest
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgesMigrateRequest:
    def test_create_minimal_request(self):
        """测试创建最小迁移请求。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        assert request.source_name == "test_source"
        assert request.from_destination == "src_oss"
        assert request.from_glob == "s3://bucket/prefix/**/*.parquet"
        assert request.to_destination == "tgt_oss"
        assert request.transform_sql is None
        assert request.options == []

    def test_create_request_with_transform_sql(self):
        """测试创建带 transform_sql 的请求。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
            transform_sql="SELECT * EXCLUDE(stock_code) FROM <source>",
        )
        assert request.transform_sql == "SELECT * EXCLUDE(stock_code) FROM <source>"

    def test_create_request_with_options(self):
        """测试创建带 options 的请求。"""
        options = ["FORMAT parquet", "COMPRESSION snappy", "OVERWRITE_OR_IGNORE true"]
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
            options=options,
        )
        assert request.options == options

    def test_create_full_request(self):
        """测试创建完整请求。"""
        request = BridgesMigrateRequest(
            source_name="tushare_stock_capflow",
            from_destination="oss_finconnect",
            from_glob="finconnect/landing/tushare_stock_capflow/**/*.parquet",
            to_destination="oss_fortress",
            transform_sql="SELECT * EXCLUDE(stock_code) FROM <source>",
            options=["FORMAT parquet", "COMPRESSION snappy"],
        )
        assert request.source_name == "tushare_stock_capflow"
        assert request.from_destination == "oss_finconnect"
        assert request.from_glob == "finconnect/landing/tushare_stock_capflow/**/*.parquet"
        assert request.to_destination == "oss_fortress"
        assert request.transform_sql == "SELECT * EXCLUDE(stock_code) FROM <source>"
        assert request.options == ["FORMAT parquet", "COMPRESSION snappy"]


# ──────────────────────────────────────────────────────────────────────────────
# TestRequestID
# ──────────────────────────────────────────────────────────────────────────────


class TestRequestID:
    def test_id_is_generated(self):
        """测试 ID 自动生成。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        assert request.id is not None
        assert len(request.id) > 0

    def test_id_has_prefix(self):
        """测试 ID 包含前缀。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        assert request.id.startswith("mig-")

    def test_id_length(self):
        """测试 ID 长度正确（prefix + '-' + 8字符）。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        # id_prefix = "mig" (3) + "-" (1) + id_length (8) = 12
        assert len(request.id) == 12

    def test_different_requests_have_different_ids(self):
        """测试不同请求有不同的 ID。"""
        request1 = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        request2 = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        assert request1.id != request2.id


# ──────────────────────────────────────────────────────────────────────────────
# TestRequestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestRequestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        exported = request.export()
        assert isinstance(exported, dict)

    def test_export_contains_id(self):
        """测试 export() 包含 id。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        exported = request.export()
        assert "id" in exported
        assert exported["id"] == request.id

    def test_export_contains_all_fields(self):
        """测试 export() 包含所有字段。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
            transform_sql="SELECT * FROM <source>",
        )
        exported = request.export()
        assert "source_name" in exported
        assert "from_destination" in exported
        assert "from_glob" in exported
        assert "to_destination" in exported
        assert "transform_sql" in exported
        assert exported["source_name"] == "test_source"
        assert exported["from_destination"] == "src_oss"
        assert exported["to_destination"] == "tgt_oss"
