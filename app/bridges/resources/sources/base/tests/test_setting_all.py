"""
综合测试：app.bridges.resources.sources.base.setting

覆盖范围
--------
- TestCoolantSetting     interval 字段验证与导出
- TestPaginateSetting    page_size/max_pages 字段验证与导出
- TestPartitionSetting   prefix/column 字段验证与导出
- TestRetrySetting       max_retries/interval/backoff_rate 字段验证与导出
- TestBaseSourceSetting  所有字段验证、from_yaml 加载、export 导出
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.bridges.resources.sources.base.setting import (
    BaseSourceSetting,
    CoolantSetting,
    PaginateSetting,
    PartitionSetting,
    RetrySetting,
)

# ──────────────────────────────────────────────────────────────────────────────
# TestCoolantSetting
# ──────────────────────────────────────────────────────────────────────────────


class TestCoolantSetting:
    def test_interval_none_by_default(self):
        s = CoolantSetting()
        assert s.interval is None

    def test_interval_accepts_float(self):
        s = CoolantSetting(interval=1.5)
        assert s.interval == 1.5

    def test_interval_accepts_int(self):
        s = CoolantSetting(interval=2)
        assert s.interval == 2

    def test_interval_accepts_none(self):
        s = CoolantSetting(interval=None)
        assert s.interval is None

    def test_export_includes_interval(self):
        s = CoolantSetting(interval=1.0)
        exported = s.export()
        assert "interval" in exported
        assert exported["interval"] == 1.0

    def test_export_includes_category(self):
        s = CoolantSetting()
        exported = s.export()
        assert "category" in exported
        assert exported["category"] == "CoolantSetting"


# ──────────────────────────────────────────────────────────────────────────────
# TestPaginateSetting
# ──────────────────────────────────────────────────────────────────────────────


class TestPaginateSetting:
    def test_page_size_none_by_default(self):
        s = PaginateSetting()
        assert s.page_size is None

    def test_max_pages_none_by_default(self):
        s = PaginateSetting()
        assert s.max_pages is None

    def test_page_size_accepts_int(self):
        s = PaginateSetting(page_size=100)
        assert s.page_size == 100

    def test_max_pages_accepts_int(self):
        s = PaginateSetting(max_pages=10)
        assert s.max_pages == 10

    def test_export_includes_both_fields(self):
        s = PaginateSetting(page_size=50, max_pages=5)
        exported = s.export()
        assert exported["page_size"] == 50
        assert exported["max_pages"] == 5

    def test_export_includes_category(self):
        s = PaginateSetting()
        exported = s.export()
        assert "category" in exported
        assert exported["category"] == "PaginateSetting"


# ──────────────────────────────────────────────────────────────────────────────
# TestPartitionSetting
# ──────────────────────────────────────────────────────────────────────────────


class TestPartitionSetting:
    def test_prefix_is_required(self):
        with pytest.raises(Exception):  # ValidationError
            PartitionSetting(column="date")

    def test_column_is_required(self):
        with pytest.raises(Exception):  # ValidationError
            PartitionSetting(prefix="dt")

    def test_prefix_and_column_are_stored(self):
        s = PartitionSetting(prefix="date", column="trade_date")
        assert s.prefix == "date"
        assert s.column == "trade_date"

    def test_export_includes_both_fields(self):
        s = PartitionSetting(prefix="date", column="trade_date")
        exported = s.export()
        assert exported["prefix"] == "date"
        assert exported["column"] == "trade_date"

    def test_export_includes_category(self):
        s = PartitionSetting(prefix="dt", column="date")
        exported = s.export()
        assert "category" in exported
        assert exported["category"] == "PartitionSetting"


# ──────────────────────────────────────────────────────────────────────────────
# TestRetrySetting
# ──────────────────────────────────────────────────────────────────────────────


class TestRetrySetting:
    def test_max_retries_none_by_default(self):
        s = RetrySetting()
        assert s.max_retries is None

    def test_interval_none_by_default(self):
        s = RetrySetting()
        assert s.interval is None

    def test_backoff_rate_none_by_default(self):
        s = RetrySetting()
        assert s.backoff_rate is None

    def test_max_retries_accepts_int(self):
        s = RetrySetting(max_retries=3)
        assert s.max_retries == 3

    def test_interval_accepts_float(self):
        s = RetrySetting(interval=1.5)
        assert s.interval == 1.5

    def test_backoff_rate_accepts_float(self):
        s = RetrySetting(backoff_rate=2.0)
        assert s.backoff_rate == 2.0

    def test_export_includes_all_fields(self):
        s = RetrySetting(max_retries=5, interval=1.0, backoff_rate=2.0)
        exported = s.export()
        assert exported["max_retries"] == 5
        assert exported["interval"] == 1.0
        assert exported["backoff_rate"] == 2.0

    def test_export_includes_category(self):
        s = RetrySetting()
        exported = s.export()
        assert "category" in exported
        assert exported["category"] == "RetrySetting"


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseSourceSetting
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseSourceSetting:
    def test_name_is_required(self):
        with pytest.raises(Exception):  # ValidationError
            BaseSourceSetting(
                provider_type="tushare",
                method="daily",
                strategy="by_date",
                partition=PartitionSetting(prefix="date", column="trade_date"),
            )

    def test_provider_type_is_required(self):
        with pytest.raises(Exception):  # ValidationError
            BaseSourceSetting(
                name="test",
                method="daily",
                strategy="by_date",
                partition=PartitionSetting(prefix="date", column="trade_date"),
            )

    def test_method_is_required(self):
        with pytest.raises(Exception):  # ValidationError
            BaseSourceSetting(
                name="test",
                provider_type="tushare",
                strategy="by_date",
                partition=PartitionSetting(prefix="date", column="trade_date"),
            )

    def test_strategy_is_required(self):
        with pytest.raises(Exception):  # ValidationError
            BaseSourceSetting(
                name="test",
                provider_type="tushare",
                method="daily",
                partition=PartitionSetting(prefix="date", column="trade_date"),
            )

    def test_partition_is_required(self):
        with pytest.raises(Exception):  # ValidationError
            BaseSourceSetting(
                name="test",
                provider_type="tushare",
                method="daily",
                strategy="by_date",
            )

    def test_retry_defaults_to_empty_retrysetting(self):
        s = BaseSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
        )
        assert isinstance(s.retry, RetrySetting)
        assert s.retry.max_retries is None

    def test_params_defaults_to_empty_list(self):
        s = BaseSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
        )
        assert s.params == []

    def test_fields_defaults_to_empty_list(self):
        s = BaseSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
        )
        assert s.fields == []

    def test_all_required_fields_are_stored(self):
        s = BaseSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
        )
        assert s.name == "test"
        assert s.provider_type == "tushare"
        assert s.method == "daily"
        assert s.strategy == "by_date"

    def test_params_accepts_list_of_strings(self):
        s = BaseSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
            params=["date", "symbol"],
        )
        assert s.params == ["date", "symbol"]

    def test_fields_accepts_list_of_strings(self):
        s = BaseSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
            fields=["ts_code", "trade_date", "close"],
        )
        assert s.fields == ["ts_code", "trade_date", "close"]

    def test_export_includes_all_fields(self):
        s = BaseSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
            params=["date"],
            fields=["close"],
        )
        exported = s.export()
        assert exported["name"] == "test"
        assert exported["provider_type"] == "tushare"
        assert exported["method"] == "daily"
        assert exported["strategy"] == "by_date"
        assert "partition" in exported
        assert "retry" in exported
        assert exported["params"] == ["date"]
        assert exported["fields"] == ["close"]

    def test_export_partition_is_dict(self):
        s = BaseSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
        )
        exported = s.export()
        assert isinstance(exported["partition"], dict)
        assert exported["partition"]["prefix"] == "date"

    def test_export_retry_is_dict(self):
        s = BaseSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
            retry=RetrySetting(max_retries=3),
        )
        exported = s.export()
        assert isinstance(exported["retry"], dict)
        assert exported["retry"]["max_retries"] == 3

    def test_from_yaml_loads_valid_file(self, tmp_path: Path):
        yaml_content = {
            "name": "stock_daily",
            "provider_type": "tushare",
            "method": "daily",
            "strategy": "by_date",
            "partition": {
                "prefix": "date",
                "column": "trade_date",
            },
            "params": ["date"],
            "fields": ["ts_code", "close"],
        }
        p = tmp_path / "test.yaml"
        p.write_text(yaml.dump(yaml_content), encoding="utf-8")
        s = BaseSourceSetting.from_yaml(p)
        assert s.name == "stock_daily"
        assert s.provider_type == "tushare"
        assert s.params == ["date"]

    def test_from_yaml_raises_on_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            BaseSourceSetting.from_yaml(tmp_path / "missing.yaml")

    def test_from_yaml_raises_on_invalid_data(self, tmp_path: Path):
        yaml_content = {"name": "test"}  # Missing required fields
        p = tmp_path / "invalid.yaml"
        p.write_text(yaml.dump(yaml_content), encoding="utf-8")
        with pytest.raises(Exception):  # ValidationError
            BaseSourceSetting.from_yaml(p)
