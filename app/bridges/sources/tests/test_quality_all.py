"""
综合测试：app.bridges.sources.quality

覆盖范围
--------
- TestSourceQuality    实例化、数据质量指标计算
- TestEmptyData        空数据集的处理
- TestDataMetrics      行数、列数、重复数、主键重复数等指标
- TestExport           export() 和 describe() 方法
"""

from __future__ import annotations

import json

import polars as pl

from app.bridges.sources.quality import SourceQuality

# ──────────────────────────────────────────────────────────────────────────────
# TestSourceQuality
# ──────────────────────────────────────────────────────────────────────────────


class TestSourceQuality:
    def test_instantiation_with_empty_dataframe(self):
        """测试使用空 DataFrame 实例化。"""
        df = pl.DataFrame()
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.source_name == "test_source"
        assert quality.source_context_id == "sctx_123"
        assert quality.data_is_empty is True

    def test_instantiation_with_data(self):
        """测试使用数据实例化。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "value": [10, 20, 30],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.data_is_empty is False
        assert quality.data_size_height == 3
        assert quality.data_size_width == 2

    def test_extra_fields_are_stored(self):
        """测试 extra 字段被存储。"""
        df = pl.DataFrame()
        extra = {"status": "SUCCESS", "started_at": "2024-01-01"}
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            extra=extra,
        )
        assert quality.extra == extra


# ──────────────────────────────────────────────────────────────────────────────
# TestEmptyData
# ──────────────────────────────────────────────────────────────────────────────


class TestEmptyData:
    def test_empty_data_metrics(self):
        """测试空数据的指标。"""
        df = pl.DataFrame()
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.data_is_empty is True
        assert quality.data_size_height == 0
        assert quality.data_size_width == 0
        assert quality.primary_keys == []
        assert quality.row_distinct_count == 0
        assert quality.row_duplicates == 0

    def test_empty_data_with_primary_keys_specified(self):
        """测试空数据但指定了主键的情况。"""
        df = pl.DataFrame()
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["id", "date"],
        )
        assert quality.primary_keys == []
        assert quality.primary_distinct_count == 0


# ──────────────────────────────────────────────────────────────────────────────
# TestDataMetrics
# ──────────────────────────────────────────────────────────────────────────────


class TestDataMetrics:
    def test_data_size_metrics(self):
        """测试数据大小指标。"""
        df = pl.DataFrame(
            {
                "a": [1, 2, 3],
                "b": [4, 5, 6],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.data_size_height == 3
        assert quality.data_size_width == 2
        assert quality.data_approx_bytes > 0

    def test_row_duplicates_detection(self):
        """测试行重复检测。"""
        df = pl.DataFrame(
            {
                "a": [1, 2, 2, 3],
                "b": [4, 5, 5, 6],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.row_distinct_count == 3
        assert quality.row_duplicates == 1
        assert quality.row_duplicates_rate == 0.25

    def test_primary_key_metrics(self):
        """测试主键指标。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3, 4],
                "value": [10, 20, 30, 40],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["id"],
        )
        assert quality.primary_keys == ["id"]
        assert quality.primary_distinct_count == 4
        assert quality.primary_duplicate_count == 0
        assert quality.primary_null_count == 0

    def test_primary_key_duplicates(self):
        """测试主键重复检测。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 2, 3],
                "value": [10, 20, 25, 30],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["id"],
        )
        assert quality.primary_distinct_count == 3
        assert quality.primary_duplicate_count == 1
        assert quality.primary_duplicate_rate == 0.25

    def test_primary_key_nulls(self):
        """测试主键空值检测。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, None, 4],
                "value": [10, 20, 30, 40],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["id"],
        )
        assert quality.primary_null_count == 1
        assert quality.primary_null_rate == 0.25

    def test_column_metrics(self):
        """测试列级别指标。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "value": [10, None, 30],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["id"],
        )
        assert "id" in quality.columns
        assert "value" in quality.columns
        assert quality.columns["id"]["is_primary"] is True
        assert quality.columns["value"]["is_primary"] is False
        assert quality.columns["value"]["null_count"] == 1

    def test_nonexistent_primary_key_ignored(self):
        """测试不存在的主键被忽略。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "value": [10, 20, 30],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["id", "nonexistent"],
        )
        assert quality.primary_keys == ["id"]


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        df = pl.DataFrame({"a": [1, 2, 3]})
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.export()
        assert isinstance(result, dict)

    def test_export_contains_required_fields(self):
        """测试 export() 包含必需字段。"""
        df = pl.DataFrame({"a": [1, 2, 3]})
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.export()
        assert "source_name" in result
        assert "source_context_id" in result
        assert "data" in result
        assert "primary_keys" in result
        assert "rows" in result
        assert "columns" in result

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        df = pl.DataFrame({"a": [1, 2, 3]})
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.describe()
        assert isinstance(result, str)

    def test_describe_is_valid_json(self):
        """测试 describe() 返回有效 JSON。"""
        df = pl.DataFrame({"a": [1, 2, 3]})
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_report_returns_dataframe(self):
        """测试 report() 返回 DataFrame。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "value": [10, 20, 30],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.report()
        assert isinstance(result, pl.DataFrame)

    def test_report_has_one_row_per_column(self):
        """测试 report() 每列生成一行。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "value": [10, 20, 30],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.report()
        assert result.height == 2  # 2 columns

    def test_report_contains_column_metrics(self):
        """测试 report() 包含列指标。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
            }
        )
        quality = SourceQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.report()
        assert "column_name" in result.columns
        assert "column_type" in result.columns
        assert "null_count" in result.columns
        assert "distinct_count" in result.columns
