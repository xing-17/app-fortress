"""
综合测试：app.bridges.migrate.node.context

覆盖范围
--------
- TestMigrateNodeContext   实例化、字段验证、ID 生成
- TestValidation           必填字段验证、destinations 非空验证
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.bridges.migrate.node.context import MigrateNodeContext

# ── 测试数据准备 ──────────────────────────────────────────────────────────────


def _create_mock_destination():
    """创建符合 BaseDestination 接口的 mock 对象"""
    from app.bridges.resources.destinations.base.destination import BaseDestination

    dest = Mock(spec=BaseDestination)
    dest.name = "mock_dest"
    return dest


# ──────────────────────────────────────────────────────────────────────────────
# TestMigrateNodeContext
# ──────────────────────────────────────────────────────────────────────────────


class TestMigrateNodeContext:
    def test_instantiation_with_required_fields(self):
        """测试使用必填字段实例化。"""
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
        )
        assert ctx.request_id == "req_123"
        assert ctx.source_name == "test_source"
        assert ctx.from_destination.name == "mock_dest"
        assert ctx.from_glob == "s3://bucket/from/**/*.parquet"
        assert ctx.to_destination.name == "mock_dest"
        assert ctx.to_glob == "s3://bucket/to/**/*.parquet"

    def test_id_is_generated_automatically(self):
        """测试 ID 自动生成。"""
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
        )
        assert ctx.id is not None
        assert isinstance(ctx.id, str)

    def test_id_prefix_is_mignctx(self):
        """测试 ID 前缀为 mignctx。"""
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
        )
        assert ctx.id.startswith("mignctx")

    def test_id_length_is_correct(self):
        """测试 ID 长度正确（prefix + length）。"""
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
        )
        # ID = prefix(7) + "_" + random(12) = 20
        assert len(ctx.id) == 7 + 1 + 12

    def test_transform_sql_is_optional(self):
        """测试 transform_sql 可选。"""
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
        )
        assert ctx.transform_sql is None

    def test_transform_sql_can_be_provided(self):
        """测试可以提供 transform_sql。"""
        sql = "SELECT * FROM <source> WHERE date > '2024-01-01'"
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
            transform_sql=sql,
        )
        assert ctx.transform_sql == sql

    def test_options_default_to_empty_list(self):
        """测试 options 默认为空列表。"""
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
        )
        assert ctx.options == []

    def test_options_can_be_provided(self):
        """测试可以提供 options。"""
        options = ["FORMAT parquet", "COMPRESSION snappy"]
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
            options=options,
        )
        assert ctx.options == options

    def test_extensions_default_to_empty_list(self):
        """测试 extensions 默认为空列表。"""
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
        )
        assert ctx.extensions == []

    def test_extensions_can_be_provided(self):
        """测试可以提供 extensions。"""
        extensions = ["httpfs", "parquet"]
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
            extensions=extensions,
        )
        assert ctx.extensions == extensions

    def test_identifier_property(self):
        """测试 identifier 属性。"""
        ctx = MigrateNodeContext(
            request_id="req_123",
            source_name="test_source",
            from_destination=_create_mock_destination(),
            from_glob="s3://bucket/from/**/*.parquet",
            to_destination=_create_mock_destination(),
            to_glob="s3://bucket/to/**/*.parquet",
        )
        assert ctx.identifier == f"test_source::{ctx.id}"


# ──────────────────────────────────────────────────────────────────────────────
# TestValidation
# ──────────────────────────────────────────────────────────────────────────────


class TestValidation:
    def test_missing_request_id_raises_error(self):
        """测试缺少 request_id 抛出错误。"""
        with pytest.raises(ValidationError):
            MigrateNodeContext(
                source_name="test_source",
                from_destination=_create_mock_destination(),
                from_glob="s3://bucket/from/**/*.parquet",
                to_destination=_create_mock_destination(),
                to_glob="s3://bucket/to/**/*.parquet",
            )

    def test_missing_source_name_raises_error(self):
        """测试缺少 source_name 抛出错误。"""
        with pytest.raises(ValidationError):
            MigrateNodeContext(
                request_id="req_123",
                from_destination=_create_mock_destination(),
                from_glob="s3://bucket/from/**/*.parquet",
                to_destination=_create_mock_destination(),
                to_glob="s3://bucket/to/**/*.parquet",
            )

    def test_missing_from_destination_raises_error(self):
        """测试缺少 from_destination 抛出错误。"""
        with pytest.raises(ValidationError):
            MigrateNodeContext(
                request_id="req_123",
                source_name="test_source",
                from_glob="s3://bucket/from/**/*.parquet",
                to_destination=_create_mock_destination(),
                to_glob="s3://bucket/to/**/*.parquet",
            )

    def test_missing_from_glob_raises_error(self):
        """测试缺少 from_glob 抛出错误。"""
        with pytest.raises(ValidationError):
            MigrateNodeContext(
                request_id="req_123",
                source_name="test_source",
                from_destination=_create_mock_destination(),
                to_destination=_create_mock_destination(),
                to_glob="s3://bucket/to/**/*.parquet",
            )

    def test_missing_to_destination_raises_error(self):
        """测试缺少 to_destination 抛出错误。"""
        with pytest.raises(ValidationError):
            MigrateNodeContext(
                request_id="req_123",
                source_name="test_source",
                from_destination=_create_mock_destination(),
                from_glob="s3://bucket/from/**/*.parquet",
                to_glob="s3://bucket/to/**/*.parquet",
            )

    def test_missing_to_glob_raises_error(self):
        """测试缺少 to_glob 抛出错误。"""
        with pytest.raises(ValidationError):
            MigrateNodeContext(
                request_id="req_123",
                source_name="test_source",
                from_destination=_create_mock_destination(),
                from_glob="s3://bucket/from/**/*.parquet",
                to_destination=_create_mock_destination(),
            )
