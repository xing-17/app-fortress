"""
综合测试：app.bridges.migrate._service.request

覆盖范围
--------
- TestMigrateRequest    实例化、字段验证、ID 生成
- TestExport            export() 和 describe() 方法
"""

from __future__ import annotations

import json

from app.bridges.migrate._service.request import MigrateRequest

# ──────────────────────────────────────────────────────────────────────────────
# TestMigrateRequest
# ──────────────────────────────────────────────────────────────────────────────


class TestMigrateRequest:
    def test_instantiation_with_required_fields(self):
        """测试使用必填字段实例化。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        assert req.source_name == "test_source"
        assert req.from_destination == "oss_source"
        assert req.from_glob == "s3://bucket/from/**/*.parquet"
        assert req.to_destination == "oss_target"

    def test_id_is_generated_automatically(self):
        """测试 ID 自动生成。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        assert req.id is not None
        assert isinstance(req.id, str)

    def test_id_prefix_is_mig(self):
        """测试 ID 前缀为 mig。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        assert req.id.startswith("mig")

    def test_id_length_is_correct(self):
        """测试 ID 长度正确（prefix + '_' + length）。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        # id_prefix="mig"(3) + "_"(1) + id_length=8 = 12
        assert len(req.id) == 3 + 1 + 8

    def test_two_requests_have_different_ids(self):
        """测试两个请求有不同的 ID。"""
        req1 = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        req2 = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        assert req1.id != req2.id

    def test_created_at_is_set(self):
        """测试 created_at 自动设置。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        assert req.created_at is not None

    def test_category_is_class_name(self):
        """测试 category 为类名。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        assert req.category == "MigrateRequest"

    def test_transform_sql_is_optional(self):
        """测试 transform_sql 可选。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        assert req.transform_sql is None

    def test_transform_sql_can_be_provided(self):
        """测试可以提供 transform_sql。"""
        sql = "SELECT * FROM <source> WHERE date > '2024-01-01'"
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
            transform_sql=sql,
        )
        assert req.transform_sql == sql

    def test_options_default_to_empty_list(self):
        """测试 options 默认为空列表。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        assert req.options == []

    def test_options_can_be_provided(self):
        """测试可以提供 options。"""
        options = ["FORMAT parquet", "COMPRESSION snappy"]
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
            options=options,
        )
        assert req.options == options

    def test_extensions_default_to_empty_list(self):
        """测试 extensions 默认为空列表。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        assert req.extensions == []

    def test_extensions_can_be_provided(self):
        """测试可以提供 extensions。"""
        extensions = ["httpfs", "parquet"]
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
            extensions=extensions,
        )
        assert req.extensions == extensions


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_contains_source_name(self):
        """测试 export() 包含 source_name 字段。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        result = req.export()
        assert result["source_name"] == "test_source"

    def test_export_contains_from_destination(self):
        """测试 export() 包含 from_destination 字段。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        result = req.export()
        assert result["from_destination"] == "oss_source"

    def test_export_contains_from_glob(self):
        """测试 export() 包含 from_glob 字段。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        result = req.export()
        assert result["from_glob"] == "s3://bucket/from/**/*.parquet"

    def test_export_contains_to_destination(self):
        """测试 export() 包含 to_destination 字段。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        result = req.export()
        assert result["to_destination"] == "oss_target"

    def test_export_contains_transform_sql(self):
        """测试 export() 包含 transform_sql 字段。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
            transform_sql="SELECT * FROM <source>",
        )
        result = req.export()
        assert result["transform_sql"] == "SELECT * FROM <source>"

    def test_export_contains_options(self):
        """测试 export() 包含 options 字段。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
            options=["FORMAT parquet"],
        )
        result = req.export()
        assert result["options"] == ["FORMAT parquet"]

    def test_export_contains_extensions(self):
        """测试 export() 包含 extensions 字段。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
            extensions=["httpfs"],
        )
        result = req.export()
        assert result["extensions"] == ["httpfs"]

    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        result = req.export()
        assert isinstance(result, dict)

    def test_describe_returns_valid_json(self):
        """测试 describe() 返回有效 JSON 字符串。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        result = req.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_contains_source_name(self):
        """测试 describe() 包含 source_name 数据。"""
        req = MigrateRequest(
            source_name="test_source",
            from_destination="oss_source",
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination="oss_target",
        )
        result = json.loads(req.describe())
        assert result["source_name"] == "test_source"
