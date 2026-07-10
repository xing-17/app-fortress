"""
综合测试：app.bridges.resources.sources.instance.tushare.source

覆盖范围
--------
- TestInit              __init__ 正确初始化并创建 coolant 和 paginate 实例
- TestResolveCoolant    _resolve_coolant() 从配置正确创建 Coolant 实例
- TestResolvePaginate   _resolve_paginate() 从配置正确创建 Paginate 实例
- TestBuildParams       build_params() 正确组装参数字典（包含 fields 处理）
- TestFetchAll          _fetch_all() 分页获取数据的完整逻辑
- TestFromYaml          from_yaml() 从 YAML 文件加载配置
- TestExport            export() 返回完整配置信息
- TestInheritance       验证正确继承 BaseSource
- TestRegistration      验证注册到 SourceFactory
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import polars as pl
import yaml

from app.bridges.resources.accessory.coolant import Coolant
from app.bridges.resources.accessory.paginate import Paginate
from app.bridges.resources.sources.base.factory import SourceFactory
from app.bridges.resources.sources.base.setting import (
    CoolantSetting,
    PaginateSetting,
    PartitionSetting,
)
from app.bridges.resources.sources.base.source import BaseSource
from app.bridges.resources.sources.instance.tushare.setting import TushareSourceSetting
from app.bridges.resources.sources.instance.tushare.source import TushareSource

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


_MOCK_SETTING = _create_minimal_setting()


# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    def test_setting_is_stored(self):
        """验证 setting 被正确存储"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert source.setting is setting

    def test_name_set_from_setting(self):
        """验证 name 从 setting 获取"""
        setting = _create_minimal_setting(name="my_source")
        source = TushareSource(setting=setting)
        assert source.name == "my_source"

    def test_provider_type_set_from_setting(self):
        """验证 provider_type 从 setting 获取"""
        setting = _create_minimal_setting(provider_type="tushare")
        source = TushareSource(setting=setting)
        assert source.provider_type == "tushare"

    def test_coolant_is_created(self):
        """验证 coolant 实例被创建"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert isinstance(source.coolant, Coolant)

    def test_paginate_is_created(self):
        """验证 paginate 实例被创建"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert isinstance(source.paginate, Paginate)

    def test_coolant_is_not_none(self):
        """验证 coolant 不为 None"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert source.coolant is not None

    def test_paginate_is_not_none(self):
        """验证 paginate 不为 None"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert source.paginate is not None


# ──────────────────────────────────────────────────────────────────────────────
# TestResolveCoolant
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveCoolant:
    def test_coolant_created_with_setting_interval(self):
        """验证使用 setting 的 interval 创建 Coolant"""
        coolant_setting = CoolantSetting(interval=1.5)
        setting = _create_minimal_setting(coolant=coolant_setting)
        source = TushareSource(setting=setting)
        assert source.coolant.interval == 1.5

    def test_coolant_with_zero_interval(self):
        """验证 interval 为 0 时正确创建"""
        coolant_setting = CoolantSetting(interval=0)
        setting = _create_minimal_setting(coolant=coolant_setting)
        source = TushareSource(setting=setting)
        assert source.coolant.interval == 0.0

    def test_coolant_with_none_interval_uses_default(self):
        """验证 interval 为 None 时使用默认值"""
        coolant_setting = CoolantSetting(interval=None)
        setting = _create_minimal_setting(coolant=coolant_setting)
        source = TushareSource(setting=setting)
        # Coolant 的默认值是 0.0
        assert source.coolant.interval == 0.0

    @patch("app.bridges.resources.sources.base.source.Coolant")
    def test_resolve_coolant_calls_coolant_constructor(self, mock_coolant_class):
        """验证 _resolve_coolant 调用 Coolant 构造函数"""
        mock_coolant_instance = Mock()
        mock_coolant_class.return_value = mock_coolant_instance

        coolant_setting = CoolantSetting(interval=2.0)
        setting = _create_minimal_setting(coolant=coolant_setting)
        _ = TushareSource(setting=setting)

        mock_coolant_class.assert_called_once_with(interval=2.0)


# ──────────────────────────────────────────────────────────────────────────────
# TestResolvePaginate
# ──────────────────────────────────────────────────────────────────────────────


class TestResolvePaginate:
    def test_paginate_created_with_setting_page_size(self):
        """验证使用 setting 的 page_size 创建 Paginate"""
        paginate_setting = PaginateSetting(page_size=1000, max_pages=5)
        setting = _create_minimal_setting(paginate=paginate_setting)
        source = TushareSource(setting=setting)
        assert source.paginate.page_size == 1000
        assert source.paginate.max_pages == 5

    def test_paginate_with_none_page_size_uses_default(self):
        """验证 page_size 为 None 时使用默认值"""
        paginate_setting = PaginateSetting(page_size=None, max_pages=None)
        setting = _create_minimal_setting(paginate=paginate_setting)
        source = TushareSource(setting=setting)
        # Paginate 的默认值是 2000 和 10
        assert source.paginate.page_size == 2000
        assert source.paginate.max_pages == 10

    def test_paginate_with_custom_values(self):
        """验证自定义 page_size 和 max_pages"""
        paginate_setting = PaginateSetting(page_size=500, max_pages=3)
        setting = _create_minimal_setting(paginate=paginate_setting)
        source = TushareSource(setting=setting)
        assert source.paginate.page_size == 500
        assert source.paginate.max_pages == 3

    @patch("app.bridges.resources.sources.base.source.Paginate")
    def test_resolve_paginate_calls_paginate_constructor(self, mock_paginate_class):
        """验证 _resolve_paginate 调用 Paginate 构造函数"""
        mock_paginate_instance = Mock()
        mock_paginate_class.return_value = mock_paginate_instance

        paginate_setting = PaginateSetting(page_size=1000, max_pages=5)
        setting = _create_minimal_setting(paginate=paginate_setting)
        _ = TushareSource(setting=setting)

        mock_paginate_class.assert_called_once_with(page_size=1000, max_pages=5)


# ──────────────────────────────────────────────────────────────────────────────
# TestBuildParams
# ──────────────────────────────────────────────────────────────────────────────


class TestBuildParams:
    def test_build_params_returns_dict(self):
        """验证 build_params 返回字典"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        result = source.build_params({})
        assert isinstance(result, dict)

    def test_build_params_with_no_params_returns_empty_dict(self):
        """验证无参数时返回空字典"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        result = source.build_params({})
        assert result == {}

    def test_build_params_copies_input_params(self):
        """验证复制输入参数"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        params = {"trade_date": "20240101", "ts_code": "000001.SZ"}
        result = source.build_params(params)
        params = {"trade_date": "20240101", "ts_code": "000001.SZ"}
        result = source.build_params(params)
        assert result["trade_date"] == "20240101"
        assert result["ts_code"] == "000001.SZ"
        assert result is not params  # 验证是复制而非引用

    def test_build_params_with_fields_joins_to_string(self):
        """验证有 fields 时拼接为逗号分隔字符串"""
        setting = _create_minimal_setting(fields=["ts_code", "trade_date", "close"], extra={"include_fields": True})
        source = TushareSource(setting=setting)
        result = source.build_params({"date": "20240101"})
        assert result["fields"] == "ts_code,trade_date,close"
        assert result["date"] == "20240101"

    def test_build_params_without_fields_no_fields_param(self):
        """验证无 fields 时不添加 fields 参数"""
        setting = _create_minimal_setting(fields=[])
        source = TushareSource(setting=setting)
        result = source.build_params({"date": "20240101"})
        assert "fields" not in result
        assert result["date"] == "20240101"

    def test_build_params_preserves_all_param_types(self):
        """验证保留所有参数类型"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        result = source.build_params(
            {
                "date": "20240101",
                "limit": 100,
                "active": True,
                "ratio": 0.5,
            }
        )
        assert result["date"] == "20240101"
        assert result["limit"] == 100
        assert result["active"] is True
        assert result["ratio"] == 0.5


# ──────────────────────────────────────────────────────────────────────────────
# TestFetchAll
# ──────────────────────────────────────────────────────────────────────────────


class TestFetchAll:
    def test_fetch_all_returns_dataframe(self):
        """验证 _fetch_all 返回 DataFrame"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        with patch.object(source, "_call_with_retry", return_value=pl.DataFrame({"col": [1]})):
            result = source._fetch_all(provider=mock_provider, params={})

        assert isinstance(result, pl.DataFrame)

    def test_fetch_all_resets_paginate_before_loop(self):
        """验证循环前重置 paginate"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        source.paginate.offset = 100  # 设置非默认值
        with patch.object(source, "_call_with_retry", return_value=pl.DataFrame()):
            source._fetch_all(provider=mock_provider, params={})

        assert source.paginate.offset == 0

    def test_fetch_all_calls_provider_with_pagination_params(self):
        """验证调用 provider 时包含分页参数"""
        paginate = PaginateSetting(page_size=1000, max_pages=3)
        setting = _create_minimal_setting(paginate=paginate)
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        with patch.object(source, "_call_with_retry", return_value=pl.DataFrame()) as mock_call:
            source._fetch_all(provider=mock_provider, params={"date": "20240101"})

        # 验证调用包含 offset 和 limit
        call_args = mock_call.call_args_list[0][1]["params"]
        assert "offset" in call_args
        assert "limit" in call_args
        assert call_args["limit"] == 1000

    def test_fetch_all_stops_on_empty_dataframe(self):
        """验证遇到空 DataFrame 时停止"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        with patch.object(source, "_call_with_retry", return_value=pl.DataFrame()) as mock_call:
            source._fetch_all(provider=mock_provider, params={})

        # 只调用一次就停止
        assert mock_call.call_count == 1

    def test_fetch_all_stops_on_none_response(self):
        """验证遇到 None 响应时停止"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        with patch.object(source, "_call_with_retry", return_value=None) as mock_call:
            source._fetch_all(provider=mock_provider, params={})

        # 只调用一次就停止
        assert mock_call.call_count == 1

    def test_fetch_all_stops_on_partial_page(self):
        """验证遇到部分页时停止（最后一页）"""
        paginate = PaginateSetting(page_size=100, max_pages=5)
        setting = _create_minimal_setting(paginate=paginate)
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        # 返回小于 page_size 的数据
        with patch.object(source, "_call_with_retry", return_value=pl.DataFrame({"col": range(50)})) as mock_call:
            source._fetch_all(provider=mock_provider, params={})

        # 只调用一次就停止
        assert mock_call.call_count == 1

    def test_fetch_all_continues_on_full_page(self):
        """验证满页时继续翻页"""
        paginate = PaginateSetting(page_size=100, max_pages=3)
        setting = _create_minimal_setting(paginate=paginate)
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        # 前两次返回满页，第三次返回空
        responses = [
            pl.DataFrame({"col": range(100)}),
            pl.DataFrame({"col": range(100)}),
            pl.DataFrame(),
        ]
        with patch.object(source, "_call_with_retry", side_effect=responses):
            result = source._fetch_all(provider=mock_provider, params={})

        # 应该获取到 200 行
        assert len(result) == 200

    def test_fetch_all_respects_max_pages(self):
        """验证尊重 max_pages 限制"""
        paginate = PaginateSetting(page_size=100, max_pages=2)
        setting = _create_minimal_setting(paginate=paginate)
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        # 始终返回满页
        with patch.object(source, "_call_with_retry", return_value=pl.DataFrame({"col": range(100)})) as mock_call:
            source._fetch_all(provider=mock_provider, params={})

        # 最多调用 max_pages 次
        assert mock_call.call_count == 2

    def test_fetch_all_calls_coolant_between_pages(self):
        """验证翻页之间调用 coolant"""
        paginate = PaginateSetting(page_size=100, max_pages=3)
        setting = _create_minimal_setting(paginate=paginate)
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        # 前两次返回满页，第三次返回空
        responses = [
            pl.DataFrame({"col": range(100)}),
            pl.DataFrame({"col": range(100)}),
            pl.DataFrame(),
        ]
        with patch.object(source, "_call_with_retry", side_effect=responses):
            with patch.object(source.coolant, "run") as mock_coolant:
                source._fetch_all(provider=mock_provider, params={})

        # 翻页 2 次，coolant 调用 2 次
        assert mock_coolant.call_count == 2

    def test_fetch_all_increments_paginate_offset(self):
        """验证翻页时正确递增 offset"""
        paginate = PaginateSetting(page_size=100, max_pages=3)
        setting = _create_minimal_setting(paginate=paginate)
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        responses = [
            pl.DataFrame({"col": range(100)}),
            pl.DataFrame({"col": range(100)}),
            pl.DataFrame(),
        ]

        call_offsets = []

        def capture_offset(*args, **kwargs):
            call_offsets.append(source.paginate.offset)
            return responses[len(call_offsets) - 1]

        with patch.object(source, "_call_with_retry", side_effect=capture_offset):
            source._fetch_all(provider=mock_provider, params={})

        # 验证 offset 递增
        assert call_offsets == [0, 100, 200]

    def test_fetch_all_concatenates_frames(self):
        """验证正确拼接多个 DataFrame"""
        paginate = PaginateSetting(page_size=100, max_pages=3)
        setting = _create_minimal_setting(paginate=paginate)
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        # 返回满页（100行）避免提前停止
        responses = [
            pl.DataFrame({"col": range(100)}),
            pl.DataFrame({"col": range(100, 200)}),
            pl.DataFrame(),
        ]
        with patch.object(source, "_call_with_retry", side_effect=responses):
            result = source._fetch_all(provider=mock_provider, params={})

        assert len(result) == 200
        assert result["col"].to_list() == list(range(200))

    def test_fetch_all_returns_empty_dataframe_when_no_data(self):
        """验证无数据时返回空 DataFrame"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)

        mock_provider = Mock()
        with patch.object(source, "_call_with_retry", return_value=pl.DataFrame()):
            result = source._fetch_all(provider=mock_provider, params={})

        assert isinstance(result, pl.DataFrame)
        assert result.is_empty()


# ──────────────────────────────────────────────────────────────────────────────
# TestFromYaml
# ──────────────────────────────────────────────────────────────────────────────


class TestFromYaml:
    def test_from_yaml_loads_config_and_creates_instance(self, tmp_path: Path):
        """验证从 YAML 加载配置并创建实例"""
        content = {
            "name": "test_tushare_source",
            "provider_type": "tushare",
            "method": "daily",
            "strategy": "by_date",
            "partition": {"prefix": "date", "column": "trade_date"},
            "fields": ["ts_code", "trade_date", "close"],
        }
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml.dump(content), encoding="utf-8")

        source = TushareSource.from_yaml(yaml_file)
        assert isinstance(source, TushareSource)
        assert source.name == "test_tushare_source"
        assert source.setting.fields == ["ts_code", "trade_date", "close"]

    def test_from_yaml_uses_tushare_source_setting(self, tmp_path: Path):
        """验证使用 TushareSourceSetting"""
        content = {
            "name": "test_source",
            "provider_type": "tushare",
            "method": "daily",
            "strategy": "by_date",
            "partition": {"prefix": "date", "column": "trade_date"},
        }
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml.dump(content), encoding="utf-8")

        source = TushareSource.from_yaml(yaml_file)
        assert isinstance(source.setting, TushareSourceSetting)
        assert source.setting.setting_type == "tushare"


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """验证 export 返回字典"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        result = source.export()
        assert isinstance(result, dict)

    def test_export_includes_setting(self):
        """验证导出包含 setting"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        result = source.export()
        assert "setting" in result
        assert isinstance(result["setting"], dict)

    def test_export_setting_contains_name(self):
        """验证导出的 setting 包含 name"""
        setting = _create_minimal_setting(name="my_source")
        source = TushareSource(setting=setting)
        result = source.export()
        assert result["setting"]["name"] == "my_source"

    def test_describe_returns_json_string(self):
        """验证 describe 返回 JSON 字符串"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        result = source.describe()
        assert isinstance(result, str)
        assert "test_source" in result


# ──────────────────────────────────────────────────────────────────────────────
# TestInheritance
# ──────────────────────────────────────────────────────────────────────────────


class TestInheritance:
    def test_is_instance_of_basesource(self):
        """验证是 BaseSource 的实例"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert isinstance(source, BaseSource)

    def test_has_setting_class_attribute(self):
        """验证有 _setting_class 类属性"""
        assert hasattr(TushareSource, "_setting_class")
        assert TushareSource._setting_class is TushareSourceSetting

    def test_implements_build_params(self):
        """验证实现了 build_params 方法"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert callable(getattr(source, "build_params", None))

    def test_implements_fetch_all(self):
        """验证实现了 _fetch_all 方法"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert callable(getattr(source, "_fetch_all", None))


# ──────────────────────────────────────────────────────────────────────────────
# TestRegistration
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistration:
    def test_registered_in_source_factory(self):
        """验证注册到 SourceFactory"""
        assert "tushare" in SourceFactory._registry
        assert SourceFactory._registry["tushare"] is TushareSource

    def test_factory_can_create_tushare_source(self, tmp_path: Path):
        """验证工厂可以创建 TushareSource"""
        content = {
            "name": "test_source",
            "provider_type": "tushare",
            "method": "daily",
            "strategy": "by_date",
            "partition": {"prefix": "date", "column": "trade_date"},
        }
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml.dump(content), encoding="utf-8")

        source = SourceFactory.from_yaml(yaml_file)
        assert isinstance(source, TushareSource)

        from app.bridges.resources.sources.base.source import BaseSource

        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert isinstance(source, BaseSource)

    def test_inherits_logplugin(self):
        """验证继承 LogPlugin"""
        from app.common.plugin import LogPlugin

        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert isinstance(source, LogPlugin)

    def test_has_log_method(self):
        """验证有 log 方法"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert hasattr(source, "log")
        assert callable(source.log)

    def test_has_info_method(self):
        """验证有 info 方法"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert hasattr(source, "info")
        assert callable(source.info)

    def test_has_debug_method(self):
        """验证有 debug 方法"""
        setting = _create_minimal_setting()
        source = TushareSource(setting=setting)
        assert hasattr(source, "debug")
        assert callable(source.debug)


# ──────────────────────────────────────────────────────────────────────────────
# TestIntegration
# ──────────────────────────────────────────────────────────────────────────────


class TestIntegration:
    def test_coolant_can_be_used(self):
        """验证 coolant 可以正常使用"""
        coolant_setting = CoolantSetting(interval=0.01)
        setting = _create_minimal_setting(coolant=coolant_setting)
        source = TushareSource(setting=setting)
        # 不应该抛出异常
        source.coolant.run()

    def test_paginate_can_be_used(self):
        """验证 paginate 可以正常使用"""
        paginate_setting = PaginateSetting(page_size=1000, max_pages=5)
        setting = _create_minimal_setting(paginate=paginate_setting)
        source = TushareSource(setting=setting)
        # 不应该抛出异常
        offset, size = source.paginate.next()
        assert offset == 0
        assert size == 1000

    def test_full_workflow(self):
        """验证完整工作流程"""
        setting = TushareSourceSetting(
            name="stock_daily",
            provider_type="tushare",
            method="daily",
            strategy="by_date",
            partition=PartitionSetting(prefix="date", column="trade_date"),
            paginate=PaginateSetting(page_size=1000, max_pages=5),
            coolant=CoolantSetting(interval=0.01),
            params=["trade_date"],
            fields=["ts_code", "close"],
            extra={"include_fields": True},
        )
        source = TushareSource(setting=setting)

        # 构建参数 - 使用字典而不是关键字参数
        params = source.build_params({"trade_date": "20240101"})
        assert params["trade_date"] == "20240101"
        assert params["fields"] == "ts_code,close"

        # 分页
        offset, size = source.paginate.next()
        assert offset == 0
        assert size == 1000

        # 冷却
        source.coolant.run()  # 不应该抛出异常

        # 导出
        exported = source.export()
        assert exported["setting"]["name"] == "stock_daily"
