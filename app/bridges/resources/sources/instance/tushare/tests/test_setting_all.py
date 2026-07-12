"""
综合测试：app.bridges.resources.sources.instance.tushare.setting

覆盖范围
--------
- TestInit         TushareSourceSetting 初始化与字段默认值
- TestPaginate     paginate 字段的配置与验证
- TestCoolant      coolant 字段的配置与验证
- TestExport       export() 方法返回完整配置字典
- TestFromYaml     from_yaml() 正确加载 YAML 配置文件
- TestInheritance  验证正确继承 BaseSourceSetting
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.bridges.resources.sources.base.setting import (
    CoolantSetting,
    PaginateSetting,
    PartitionSetting,
)
from app.bridges.resources.sources.instance.tushare.setting import TushareSourceSetting

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


def _create_minimal_setting(**kwargs):
    """创建最小化的有效 TushareSourceSetting"""
    defaults = {
        "name": "test_source",
        "provider_type": "tushare",
        "method": "daily",
        "strategy": "by_date",
        "partition": PartitionSetting(prefix="date", column="trade_date"),
    }
    defaults.update(kwargs)
    return TushareSourceSetting(**defaults)


# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    def test_inherits_base_required_fields(self):
        """验证继承基类的必填字段"""
        s = _create_minimal_setting()
        assert s.name == "test_source"
        assert s.provider_type == "tushare"
        assert s.method == "daily"
        assert s.strategy == "by_date"

    def test_paginate_defaults_to_empty_paginatesetting(self):
        """验证 paginate 默认为空的 PaginateSetting 实例"""
        s = _create_minimal_setting()
        assert isinstance(s.paginate, PaginateSetting)
        assert s.paginate.page_size is None
        assert s.paginate.max_pages is None

    def test_coolant_defaults_to_empty_coolantsetting(self):
        """验证 coolant 默认为空的 CoolantSetting 实例"""
        s = _create_minimal_setting()
        assert isinstance(s.coolant, CoolantSetting)
        assert s.coolant.interval is None

    def test_all_base_fields_are_accessible(self):
        """验证所有基类字段可访问"""
        s = _create_minimal_setting(
            params=["date"],
            fields=["ts_code", "close"],
        )
        assert s.params == ["date"]
        assert s.fields == ["ts_code", "close"]
        assert isinstance(s.partition, PartitionSetting)


# ──────────────────────────────────────────────────────────────────────────────
# TestPaginate
# ──────────────────────────────────────────────────────────────────────────────


class TestPaginate:
    def test_paginate_accepts_paginatesetting(self):
        """验证可以传入 PaginateSetting 实例"""
        paginate = PaginateSetting(page_size=1000, max_pages=5)
        s = _create_minimal_setting(paginate=paginate)
        assert s.paginate.page_size == 1000
        assert s.paginate.max_pages == 5

    def test_paginate_accepts_dict(self):
        """验证可以通过字典配置 paginate"""
        s = TushareSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition={"prefix": "date", "column": "trade_date"},
            paginate={"page_size": 2000, "max_pages": 10},
        )
        assert s.paginate.page_size == 2000
        assert s.paginate.max_pages == 10

    def test_paginate_page_size_is_optional(self):
        """验证 page_size 可选"""
        paginate = PaginateSetting(max_pages=5)
        s = _create_minimal_setting(paginate=paginate)
        assert s.paginate.page_size is None
        assert s.paginate.max_pages == 5

    def test_paginate_max_pages_is_optional(self):
        """验证 max_pages 可选"""
        paginate = PaginateSetting(page_size=1000)
        s = _create_minimal_setting(paginate=paginate)
        assert s.paginate.page_size == 1000
        assert s.paginate.max_pages is None


# ──────────────────────────────────────────────────────────────────────────────
# TestCoolant
# ──────────────────────────────────────────────────────────────────────────────


class TestCoolant:
    def test_coolant_accepts_coolantsetting(self):
        """验证可以传入 CoolantSetting 实例"""
        coolant = CoolantSetting(interval=1.5)
        s = _create_minimal_setting(coolant=coolant)
        assert s.coolant.interval == 1.5

    def test_coolant_accepts_dict(self):
        """验证可以通过字典配置 coolant"""
        s = TushareSourceSetting(
            name="test",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition={"prefix": "date", "column": "trade_date"},
            coolant={"interval": 2.0},
        )
        assert s.coolant.interval == 2.0

    def test_coolant_interval_accepts_int(self):
        """验证 interval 接受整数"""
        coolant = CoolantSetting(interval=3)
        s = _create_minimal_setting(coolant=coolant)
        assert s.coolant.interval == 3

    def test_coolant_interval_accepts_float(self):
        """验证 interval 接受浮点数"""
        coolant = CoolantSetting(interval=0.5)
        s = _create_minimal_setting(coolant=coolant)
        assert s.coolant.interval == 0.5

    def test_coolant_interval_accepts_zero(self):
        """验证 interval 接受零值"""
        coolant = CoolantSetting(interval=0)
        s = _create_minimal_setting(coolant=coolant)
        assert s.coolant.interval == 0


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """验证 export() 返回字典"""
        s = _create_minimal_setting()
        result = s.export()
        assert isinstance(result, dict)

    def test_export_includes_base_fields(self):
        """验证导出包含基类字段"""
        s = _create_minimal_setting()
        result = s.export()
        assert result["name"] == "test_source"
        assert result["provider_type"] == "tushare"
        assert result["method"] == "daily"
        assert result["strategy"] == "by_date"
        assert "partition" in result
        assert "retry" in result

    def test_export_includes_paginate(self):
        """验证导出包含 paginate"""
        paginate = PaginateSetting(page_size=1000, max_pages=5)
        s = _create_minimal_setting(paginate=paginate)
        result = s.export()
        assert "paginate" in result
        assert isinstance(result["paginate"], dict)
        assert result["paginate"]["page_size"] == 1000
        assert result["paginate"]["max_pages"] == 5

    def test_export_includes_coolant(self):
        """验证导出包含 coolant"""
        coolant = CoolantSetting(interval=1.5)
        s = _create_minimal_setting(coolant=coolant)
        result = s.export()
        assert "coolant" in result
        assert isinstance(result["coolant"], dict)
        assert result["coolant"]["interval"] == 1.5

    def test_export_paginate_is_dict_not_object(self):
        """验证导出的 paginate 是字典而非对象"""
        s = _create_minimal_setting()
        result = s.export()
        assert isinstance(result["paginate"], dict)
        assert not isinstance(result["paginate"], PaginateSetting)

    def test_export_coolant_is_dict_not_object(self):
        """验证导出的 coolant 是字典而非对象"""
        s = _create_minimal_setting()
        result = s.export()
        assert isinstance(result["coolant"], dict)
        assert not isinstance(result["coolant"], CoolantSetting)

    def test_export_with_all_fields(self):
        """验证完整配置的导出"""
        s = TushareSourceSetting(
            name="stock_daily",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
            paginate=PaginateSetting(page_size=2000, max_pages=10),
            coolant=CoolantSetting(interval=1.0),
            params=["date"],
            fields=["ts_code", "close"],
        )
        result = s.export()
        assert result["name"] == "stock_daily"
        assert result["paginate"]["page_size"] == 2000
        assert result["coolant"]["interval"] == 1.0
        assert result["params"] == ["date"]


# ──────────────────────────────────────────────────────────────────────────────
# TestFromYaml
# ──────────────────────────────────────────────────────────────────────────────


class TestFromYaml:
    def test_from_yaml_loads_valid_file(self, tmp_path: Path):
        """验证 from_yaml 正确加载有效文件"""
        yaml_content = {
            "name": "stock_daily",
            "provider_type": "tushare",
            "method": "daily",
            "strategy": "by_date",
            "partition": {"prefix": "date", "column": "trade_date"},
            "paginate": {"page_size": 1000, "max_pages": 5},
            "coolant": {"interval": 1.0},
        }
        p = tmp_path / "test.yaml"
        p.write_text(yaml.dump(yaml_content), encoding="utf-8")
        s = TushareSourceSetting.from_yaml(p)
        assert s.name == "stock_daily"
        assert s.paginate.page_size == 1000
        assert s.coolant.interval == 1.0

    def test_from_yaml_raises_on_missing_file(self, tmp_path: Path):
        """验证加载不存在的文件抛出异常"""
        with pytest.raises(FileNotFoundError):
            TushareSourceSetting.from_yaml(tmp_path / "missing.yaml")

    def test_from_yaml_populates_all_fields(self, tmp_path: Path):
        """验证 from_yaml 正确填充所有字段"""
        yaml_content = {
            "name": "stock_daily",
            "provider_type": "tushare",
            "method": "daily",
            "strategy": "by_date",
            "partition": {"prefix": "date", "column": "trade_date"},
            "paginate": {"page_size": 2000, "max_pages": 10},
            "coolant": {"interval": 0.5},
            "params": ["date", "symbol"],
            "fields": ["ts_code", "close", "open"],
        }
        p = tmp_path / "complete.yaml"
        p.write_text(yaml.dump(yaml_content), encoding="utf-8")
        s = TushareSourceSetting.from_yaml(p)
        assert s.name == "stock_daily"
        assert s.provider_type == "tushare"
        assert s.method == "daily"
        assert s.strategy == "by_date"
        assert s.partition.prefix == "date"
        assert s.partition.column == "trade_date"
        assert s.paginate.page_size == 2000
        assert s.paginate.max_pages == 10
        assert s.coolant.interval == 0.5
        assert s.params == ["date", "symbol"]
        assert s.fields == ["ts_code", "close", "open"]

    def test_from_yaml_with_missing_optional_fields(self, tmp_path: Path):
        """验证省略可选字段时使用默认值"""
        yaml_content = {
            "name": "stock_daily",
            "provider_type": "tushare",
            "method": "daily",
            "strategy": "by_date",
            "partition": {"prefix": "date", "column": "trade_date"},
        }
        p = tmp_path / "minimal.yaml"
        p.write_text(yaml.dump(yaml_content), encoding="utf-8")
        s = TushareSourceSetting.from_yaml(p)
        assert s.paginate.page_size is None
        assert s.coolant.interval is None
        assert s.params == []
        assert s.fields == []


# ──────────────────────────────────────────────────────────────────────────────
# TestInheritance
# ──────────────────────────────────────────────────────────────────────────────


class TestInheritance:
    def test_is_instance_of_basesourcesetting(self):
        """验证是 BaseSourceSetting 的实例"""
        from app.bridges.resources.sources.base.setting import BaseSourceSetting

        s = _create_minimal_setting()
        assert isinstance(s, BaseSourceSetting)

    def test_has_category_property(self):
        """验证有 category 属性"""
        s = _create_minimal_setting()
        assert hasattr(s, "category")
        assert s.category == "TushareSourceSetting"
