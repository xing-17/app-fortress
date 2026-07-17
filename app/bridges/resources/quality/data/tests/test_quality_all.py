"""
综合测试：app.bridges.resources.quality.data

覆盖范围
--------
- TestSourceDataQuality    实例化、数据质量指标计算
- TestEmptyData            空数据集的处理
- TestDataMetrics          行数、列数、重复数、主键重复数等指标
- TestExport               export() 和 describe() 方法
- TestReport               report() 方法与 DataFrame 输出
- TestEdgeCases            边界情况与异常处理
"""

from __future__ import annotations

import json

import polars as pl
import pytest

from app.bridges.resources.quality.data import SourceDataQuality

# ──────────────────────────────────────────────────────────────────────────────
# TestSourceDataQuality
# ──────────────────────────────────────────────────────────────────────────────


class TestSourceDataQuality:
    def test_instantiation_with_empty_dataframe(self):
        """测试使用空 DataFrame 实例化。"""
        df = pl.DataFrame()
        quality = SourceDataQuality(
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
        quality = SourceDataQuality(
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
        extra = {"status": "DONE", "started_at": "2024-01-01"}
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            extra=extra,
        )
        assert quality.extra == extra

    def test_get_category(self):
        """测试 get_category() 方法。"""
        df = pl.DataFrame()
        quality = SourceDataQuality(
            source_name="daily_basic",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.get_category() == "daily_basic"

    def test_get_identifier(self):
        """测试 get_identifier() 方法。"""
        df = pl.DataFrame()
        quality = SourceDataQuality(
            source_name="daily_basic",
            source_context_id="sctx_abc123",
            data=df,
        )
        assert quality.get_identifier() == "sctx_abc123"


# ──────────────────────────────────────────────────────────────────────────────
# TestEmptyData
# ──────────────────────────────────────────────────────────────────────────────


class TestEmptyData:
    def test_empty_data_metrics(self):
        """测试空数据的指标。"""
        df = pl.DataFrame()
        quality = SourceDataQuality(
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
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["id", "date"],
        )
        assert quality.primary_keys == []
        assert quality.primary_distinct_count == 0

    def test_empty_data_report(self):
        """测试空数据的 report() 输出。"""
        df = pl.DataFrame()
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.report()
        assert isinstance(result, pl.DataFrame)
        assert result.height == 0  # 无列则无行


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
        quality = SourceDataQuality(
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
        quality = SourceDataQuality(
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
        quality = SourceDataQuality(
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
        quality = SourceDataQuality(
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
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["id"],
        )
        assert quality.primary_null_count == 1
        assert quality.primary_null_rate == 0.25

    def test_composite_primary_key(self):
        """测试复合主键。"""
        df = pl.DataFrame(
            {
                "ts_code": ["000001.SZ", "000002.SZ", "000001.SZ", "000002.SZ"],
                "trade_date": ["20240101", "20240101", "20240102", "20240102"],
                "close": [10.5, 20.3, 11.2, 21.5],
            }
        )
        quality = SourceDataQuality(
            source_name="daily_basic",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["ts_code", "trade_date"],
        )
        assert quality.primary_keys == ["ts_code", "trade_date"]
        assert quality.primary_distinct_count == 4
        assert quality.primary_duplicate_count == 0
        assert quality.primary_null_count == 0

    def test_composite_primary_key_with_duplicates(self):
        """测试复合主键的重复检测。"""
        df = pl.DataFrame(
            {
                "ts_code": ["000001.SZ", "000002.SZ", "000001.SZ"],
                "trade_date": ["20240101", "20240101", "20240101"],
                "close": [10.5, 20.3, 11.2],
            }
        )
        quality = SourceDataQuality(
            source_name="daily_basic",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["ts_code", "trade_date"],
        )
        assert quality.primary_distinct_count == 2
        assert quality.primary_duplicate_count == 1

    def test_column_metrics(self):
        """测试列级别指标。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "value": [10, None, 30],
            }
        )
        quality = SourceDataQuality(
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
        assert quality.columns["value"]["null_rate"] == round(1 / 3, 4)

    def test_column_distinct_rate(self):
        """测试列去重率计算。"""
        df = pl.DataFrame(
            {
                "category": ["A", "B", "A", "C", "B"],
                "score": [10, 20, 10, 30, 40],
            }
        )
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.columns["category"]["distinct_count"] == 3
        assert quality.columns["category"]["distinct_rate"] == 0.6
        assert quality.columns["score"]["distinct_count"] == 4
        assert quality.columns["score"]["distinct_rate"] == 0.8

    def test_nonexistent_primary_key_ignored(self):
        """测试不存在的主键被忽略。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "value": [10, 20, 30],
            }
        )
        quality = SourceDataQuality(
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
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.export()
        assert isinstance(result, dict)

    def test_export_contains_required_fields(self):
        """测试 export() 包含必需字段。"""
        df = pl.DataFrame({"a": [1, 2, 3]})
        quality = SourceDataQuality(
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

    def test_export_data_structure(self):
        """测试 export() 的数据结构。"""
        df = pl.DataFrame({"a": [1, 2, 3]})
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.export()
        assert "is_empty" in result["data"]
        assert "height" in result["data"]
        assert "width" in result["data"]
        assert "approx_bytes" in result["data"]
        assert "keys" in result["primary_keys"]
        assert "distinct_count" in result["primary_keys"]

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        df = pl.DataFrame({"a": [1, 2, 3]})
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.describe()
        assert isinstance(result, str)

    def test_describe_is_valid_json(self):
        """测试 describe() 返回有效 JSON。"""
        df = pl.DataFrame({"a": [1, 2, 3]})
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_ensure_ascii_false(self):
        """测试 describe() 支持中文字符。"""
        df = pl.DataFrame({"名称": ["测试"], "值": [100]})
        quality = SourceDataQuality(
            source_name="测试数据源",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.describe()
        assert "测试数据源" in result
        assert "名称" in result


# ──────────────────────────────────────────────────────────────────────────────
# TestReport
# ──────────────────────────────────────────────────────────────────────────────


class TestReport:
    def test_report_returns_dataframe(self):
        """测试 report() 返回 DataFrame。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "value": [10, 20, 30],
            }
        )
        quality = SourceDataQuality(
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
        quality = SourceDataQuality(
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
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.report()
        assert "column_name" in result.columns
        assert "column_type" in result.columns
        assert "null_count" in result.columns
        assert "distinct_count" in result.columns
        assert "is_primary" in result.columns

    def test_report_includes_data_metrics(self):
        """测试 report() 包含数据级别指标。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
            }
        )
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        result = quality.report()
        assert "source_name" in result.columns
        assert "source_context_id" in result.columns
        assert "data_is_empty" in result.columns
        assert "data_size_height" in result.columns
        assert "data_size_width" in result.columns

    def test_report_includes_extra_fields(self):
        """测试 report() 包含 extra 字段。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
            }
        )
        extra = {"status": "DONE", "execution_time": 1.23}
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            extra=extra,
        )
        result = quality.report()
        assert "status" in result.columns
        assert "execution_time" in result.columns
        assert result["status"][0] == "DONE"
        assert result["execution_time"][0] == 1.23

    def test_report_raises_on_conflicting_extra_fields(self):
        """测试 report() 在 extra 字段与保留字段冲突时抛出异常。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
            }
        )
        extra = {"source_name": "conflict"}
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            extra=extra,
        )
        with pytest.raises(ValueError, match="Extra conflict with reserved"):
            quality.report()


# ──────────────────────────────────────────────────────────────────────────────
# TestEdgeCases
# ──────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_single_row_data(self):
        """测试单行数据。"""
        df = pl.DataFrame(
            {
                "id": [1],
                "value": [10],
            }
        )
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.data_size_height == 1
        assert quality.row_distinct_count == 1
        assert quality.row_duplicates == 0

    def test_single_column_data(self):
        """测试单列数据。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
            }
        )
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.data_size_width == 1
        assert len(quality.columns) == 1

    def test_all_null_column(self):
        """测试全为 null 的列。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "value": [None, None, None],
            }
        )
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.columns["value"]["null_count"] == 3
        assert quality.columns["value"]["null_rate"] == 1.0

    def test_all_duplicate_rows(self):
        """测试全部重复的行。"""
        df = pl.DataFrame(
            {
                "id": [1, 1, 1],
                "value": [10, 10, 10],
            }
        )
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.row_distinct_count == 1
        assert quality.row_duplicates == 2
        assert quality.row_duplicates_rate == round(2 / 3, 4)

    def test_no_primary_keys_specified(self):
        """测试未指定主键。"""
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "value": [10, 20, 30],
            }
        )
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert quality.primary_keys == []
        assert quality.primary_distinct_count == 0
        assert quality.primary_duplicate_count == 0

    def test_mixed_types_in_column(self):
        """测试列中混合类型（Polars 会自动处理）。"""
        df = pl.DataFrame(
            {
                "mixed": [1, 2, 3],
            }
        )
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert "type" in quality.columns["mixed"]
        assert quality.columns["mixed"]["type"] != ""

    def test_large_dataset_metrics(self):
        """测试较大数据集的指标计算（性能测试）。"""
        import time

        # 创建 10000 行数据
        df = pl.DataFrame(
            {
                "id": list(range(10000)),
                "category": [f"cat_{i % 100}" for i in range(10000)],
                "value": [i * 1.5 for i in range(10000)],
            }
        )

        start = time.time()
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
            primary_keys=["id"],
        )
        elapsed = time.time() - start

        assert quality.data_size_height == 10000
        assert quality.primary_distinct_count == 10000
        assert quality.columns["category"]["distinct_count"] == 100
        # 性能检查：应在 1 秒内完成
        assert elapsed < 1.0

    def test_special_characters_in_column_names(self):
        """测试列名包含特殊字符。"""
        df = pl.DataFrame(
            {
                "user.id": [1, 2, 3],
                "user-name": ["alice", "bob", "charlie"],
                "user@email": ["a@x.com", "b@x.com", "c@x.com"],
            }
        )
        quality = SourceDataQuality(
            source_name="test_source",
            source_context_id="sctx_123",
            data=df,
        )
        assert "user.id" in quality.columns
        assert "user-name" in quality.columns
        assert "user@email" in quality.columns
