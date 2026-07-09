"""
综合测试：app.bridges.resources.sources.base.source

覆盖范围
--------
- TestFromYaml           from_yaml() 类方法正确加载 YAML 并构建实例
- TestInit               __init__() 初始化所有属性
- TestResolveCoolant     _resolve_coolant() 创建 Coolant 实例
- TestResolvePaginate    _resolve_paginate() 创建 Paginate 实例
- TestResolvePartitions  _resolve_partitions() 将参数转换为分区路径
- TestCheckRetriable     _check_retriable() 判断异常是否可重试
- TestCallWithRetry      _call_with_retry() 重试逻辑与异常处理
- TestRun                run() 缓存检查、数据获取、缓存写入完整流程
- TestExport             export() 和 describe() 方法
- TestAbstractMethods    验证抽象方法必须由子类实现
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import polars as pl
import pytest
import yaml

from app.bridges.resources.sources.base.setting import (
    BaseSourceSetting,
    CoolantSetting,
    PaginateSetting,
    PartitionSetting,
    RetrySetting,
)
from app.bridges.resources.sources.base.source import BaseSource

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────


class _ConcreteSource(BaseSource):
    """用于测试的具体实现"""

    def __init__(self, setting: BaseSourceSetting) -> None:
        # 必须先初始化 mixin，才能使用 _logger
        super().__init__(setting)

    def build_params(self, params: dict[str, Any]) -> dict[str, Any]:
        return params.copy()

    def _fetch_all(self, provider, params: dict[str, Any]) -> pl.DataFrame:
        return pl.DataFrame({"col": [1, 2, 3]})


def _create_minimal_setting(**kwargs):
    """创建最小化的有效 BaseSourceSetting"""
    defaults = {
        "name": "test_source",
        "provider_type": "test",
        "method": "test_method",
        "strategy": "by_date",
        "partition": PartitionSetting(prefix="date", column="trade_date"),
    }
    defaults.update(kwargs)
    return BaseSourceSetting(**defaults)


# ──────────────────────────────────────────────────────────────────────────────
# TestFromYaml
# ──────────────────────────────────────────────────────────────────────────────


class TestFromYaml:
    def test_from_yaml_loads_setting_and_creates_instance(self, tmp_path: Path):
        """验证 from_yaml 加载配置并创建实例"""
        content = {
            "name": "test_source",
            "provider_type": "test",
            "method": "test_method",
            "strategy": "by_date",
            "partition": {"prefix": "date", "column": "trade_date"},
        }
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml.dump(content), encoding="utf-8")

        source = _ConcreteSource.from_yaml(yaml_file)
        assert isinstance(source, _ConcreteSource)
        assert source.name == "test_source"

    def test_from_yaml_uses_setting_class_attribute(self, tmp_path: Path):
        """验证使用 _setting_class 加载配置"""
        content = {
            "name": "test_source",
            "provider_type": "test",
            "method": "test_method",
            "strategy": "by_date",
            "partition": {"prefix": "date", "column": "trade_date"},
        }
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml.dump(content), encoding="utf-8")

        source = _ConcreteSource.from_yaml(yaml_file)
        assert isinstance(source.setting, BaseSourceSetting)

    def test_from_yaml_accepts_string_path(self, tmp_path: Path):
        """验证接受字符串路径"""
        content = {
            "name": "test_source",
            "provider_type": "test",
            "method": "test_method",
            "strategy": "by_date",
            "partition": {"prefix": "date", "column": "trade_date"},
        }
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml.dump(content), encoding="utf-8")

        source = _ConcreteSource.from_yaml(str(yaml_file))
        assert source.name == "test_source"


# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    def test_init_stores_setting(self):
        """验证存储 setting 属性"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        assert source.setting is setting

    def test_init_sets_name_from_setting(self):
        """验证从 setting 提取 name"""
        setting = _create_minimal_setting(name="my_source")
        source = _ConcreteSource(setting=setting)
        assert source.name == "my_source"

    def test_init_sets_provider_type_from_setting(self):
        """验证从 setting 提取 provider_type"""
        setting = _create_minimal_setting(provider_type="tushare")
        source = _ConcreteSource(setting=setting)
        assert source.provider_type == "tushare"

    def test_init_sets_tags_from_setting(self):
        """验证从 setting 提取 tags"""
        tags = {"region": "cn", "domain": "stock"}
        setting = _create_minimal_setting(tags=tags)
        source = _ConcreteSource(setting=setting)
        assert source.tags == tags

    def test_init_creates_coolant(self):
        """验证创建 Coolant 实例"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        assert source.coolant is not None

    def test_init_creates_paginate(self):
        """验证创建 Paginate 实例"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        assert source.paginate is not None


# ──────────────────────────────────────────────────────────────────────────────
# TestResolveCoolant
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveCoolant:
    def test_resolve_coolant_uses_setting_interval(self):
        """验证使用 setting 中的 interval"""
        coolant = CoolantSetting(interval=2.5)
        setting = _create_minimal_setting(coolant=coolant)
        source = _ConcreteSource(setting=setting)
        assert source.coolant.interval == 2.5

    def test_resolve_coolant_with_none_interval(self):
        """验证 interval=None 时使用默认值"""
        coolant = CoolantSetting(interval=None)
        setting = _create_minimal_setting(coolant=coolant)
        source = _ConcreteSource(setting=setting)
        assert source.coolant.interval == 0.0

    def test_resolve_coolant_with_zero_interval(self):
        """验证 interval=0 时正确传递"""
        coolant = CoolantSetting(interval=0)
        setting = _create_minimal_setting(coolant=coolant)
        source = _ConcreteSource(setting=setting)
        assert source.coolant.interval == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# TestResolvePaginate
# ──────────────────────────────────────────────────────────────────────────────


class TestResolvePaginate:
    def test_resolve_paginate_uses_setting_page_size(self):
        """验证使用 setting 中的 page_size"""
        paginate = PaginateSetting(page_size=1000, max_pages=5)
        setting = _create_minimal_setting(paginate=paginate)
        source = _ConcreteSource(setting=setting)
        assert source.paginate.page_size == 1000
        assert source.paginate.max_pages == 5

    def test_resolve_paginate_with_none_values(self):
        """验证 None 值时使用默认值"""
        paginate = PaginateSetting(page_size=None, max_pages=None)
        setting = _create_minimal_setting(paginate=paginate)
        source = _ConcreteSource(setting=setting)
        assert source.paginate.page_size == 2000  # Paginate 默认值
        assert source.paginate.max_pages == 10

    def test_resolve_paginate_with_custom_values(self):
        """验证自定义值正确传递"""
        paginate = PaginateSetting(page_size=500, max_pages=3)
        setting = _create_minimal_setting(paginate=paginate)
        source = _ConcreteSource(setting=setting)
        assert source.paginate.page_size == 500
        assert source.paginate.max_pages == 3


# ──────────────────────────────────────────────────────────────────────────────
# TestResolvePartitions
# ──────────────────────────────────────────────────────────────────────────────


class TestResolvePartitions:
    def test_resolve_partitions_returns_list_of_strings(self):
        """验证返回字符串列表"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        result = source._resolve_partitions({"date": "20240101"})
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_resolve_partitions_formats_key_value_pairs(self):
        """验证格式化为 key=value"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        result = source._resolve_partitions({"date": "20240101"})
        assert result == ["date=20240101"]

    def test_resolve_partitions_sorts_by_key(self):
        """验证按 key 排序"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        result = source._resolve_partitions({"z": "1", "a": "2", "m": "3"})
        assert result == ["a=2", "m=3", "z=1"]

    def test_resolve_partitions_with_multiple_params(self):
        """验证多参数情况"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        result = source._resolve_partitions({"date": "20240101", "symbol": "600000"})
        assert result == ["date=20240101", "symbol=600000"]

    def test_resolve_partitions_with_empty_params(self):
        """验证空参数返回空列表"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        result = source._resolve_partitions({})
        assert result == []


# ──────────────────────────────────────────────────────────────────────────────
# TestCheckRetriable
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckRetriable:
    def test_check_retriable_returns_true_when_no_patterns(self):
        """验证无 ignore_patterns 时所有异常可重试"""
        retry = RetrySetting(ignore_patterns=[])
        setting = _create_minimal_setting(retry=retry)
        source = _ConcreteSource(setting=setting)

        exc = ValueError("some error")
        assert source._check_retriable(exc) is True

    def test_check_retriable_returns_false_when_pattern_matches(self):
        """验证异常消息匹配 ignore_patterns 时不可重试"""
        retry = RetrySetting(ignore_patterns=["不存在", "invalid"])
        setting = _create_minimal_setting(retry=retry)
        source = _ConcreteSource(setting=setting)

        exc = ValueError("数据不存在")
        assert source._check_retriable(exc) is False

    def test_check_retriable_returns_true_when_pattern_not_matches(self):
        """验证异常消息不匹配 ignore_patterns 时可重试"""
        retry = RetrySetting(ignore_patterns=["不存在"])
        setting = _create_minimal_setting(retry=retry)
        source = _ConcreteSource(setting=setting)

        exc = ValueError("connection timeout")
        assert source._check_retriable(exc) is True

    def test_check_retriable_with_multiple_patterns(self):
        """验证多个 pattern 的情况"""
        retry = RetrySetting(ignore_patterns=["不存在", "invalid", "unauthorized"])
        setting = _create_minimal_setting(retry=retry)
        source = _ConcreteSource(setting=setting)

        exc1 = ValueError("invalid token")
        exc2 = ValueError("connection error")
        assert source._check_retriable(exc1) is False
        assert source._check_retriable(exc2) is True

    def test_check_retriable_partial_match(self):
        """验证部分匹配即判定为不可重试"""
        retry = RetrySetting(ignore_patterns=["不存在"])
        setting = _create_minimal_setting(retry=retry)
        source = _ConcreteSource(setting=setting)

        exc = ValueError("该数据不存在，请检查参数")
        assert source._check_retriable(exc) is False


# ──────────────────────────────────────────────────────────────────────────────
# TestCallWithRetry
# ──────────────────────────────────────────────────────────────────────────────


class TestCallWithRetry:
    def test_call_with_retry_returns_dataframe_on_success(self):
        """验证成功调用返回 DataFrame"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.call.return_value = pl.DataFrame({"col": [1, 2, 3]})

        result = source._call_with_retry(
            provider=mock_provider,
            method="test_method",
            params={"param1": "value1"},
        )

        assert isinstance(result, pl.DataFrame)
        assert len(result) == 3

    def test_call_with_retry_calls_provider_with_correct_params(self):
        """验证正确调用 provider.call"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.call.return_value = pl.DataFrame({"col": [1]})

        source._call_with_retry(
            provider=mock_provider,
            method="test_method",
            params={"param1": "value1"},
        )

        mock_provider.call.assert_called_once_with("test_method", param1="value1")

    def test_call_with_retry_retries_on_retriable_exception(self):
        """验证可重试异常会触发重试"""
        retry = RetrySetting(max_retries=2, interval=0.01, backoff_rate=1.0)
        setting = _create_minimal_setting(retry=retry)
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.call.side_effect = [
            ValueError("connection error"),
            ValueError("connection error"),
            pl.DataFrame({"col": [1]}),
        ]

        result = source._call_with_retry(
            provider=mock_provider,
            method="test_method",
            params={},
        )

        assert isinstance(result, pl.DataFrame)
        assert mock_provider.call.call_count == 3

    def test_call_with_retry_returns_none_on_non_retriable_exception(self):
        """验证不可重试异常返回 None"""
        retry = RetrySetting(max_retries=2, interval=0.01, ignore_patterns=["不存在"])
        setting = _create_minimal_setting(retry=retry)
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.call.side_effect = ValueError("数据不存在")

        result = source._call_with_retry(
            provider=mock_provider,
            method="test_method",
            params={},
        )

        assert result is None
        assert mock_provider.call.call_count == 1  # 不重试

    def test_call_with_retry_raises_on_max_retries_exceeded(self):
        """验证超过最大重试次数后抛出异常"""
        retry = RetrySetting(max_retries=1, interval=0.01, backoff_rate=1.0)
        setting = _create_minimal_setting(retry=retry)
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.call.side_effect = ValueError("connection error")

        with pytest.raises(ValueError, match="connection error"):
            source._call_with_retry(
                provider=mock_provider,
                method="test_method",
                params={},
            )

        assert mock_provider.call.call_count == 2  # 1 次初始 + 1 次重试


# ──────────────────────────────────────────────────────────────────────────────
# TestRun
# ──────────────────────────────────────────────────────────────────────────────


class TestRun:
    def test_run_returns_cached_data_when_cache_hit(self):
        """验证缓存命中时直接返回缓存数据"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.setting.use_cache = True
        mock_cache = Mock()
        mock_cache.check.return_value = True
        mock_cache.read.return_value = pl.DataFrame({"col": [10, 20]})
        mock_provider.cache = mock_cache

        result = source.run(provider=mock_provider, params={"date": "20240101"})

        assert isinstance(result, pl.DataFrame)
        assert len(result) == 2
        mock_cache.check.assert_called_once()
        mock_cache.read.assert_called_once()

    def test_run_fetches_data_when_cache_miss(self):
        """验证缓存未命中时调用 _fetch_all"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.setting.use_cache = True
        mock_cache = Mock()
        mock_cache.check.return_value = False
        mock_provider.cache = mock_cache

        with patch.object(source, "_fetch_all", return_value=pl.DataFrame({"col": [1, 2]})):
            result = source.run(provider=mock_provider, params={"date": "20240101"})

        assert isinstance(result, pl.DataFrame)
        assert len(result) == 2

    def test_run_writes_cache_after_fetch(self):
        """验证获取数据后写入缓存"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.setting.use_cache = True
        mock_cache = Mock()
        mock_cache.check.return_value = False
        mock_provider.cache = mock_cache

        with patch.object(source, "_fetch_all", return_value=pl.DataFrame({"col": [1, 2]})):
            source.run(provider=mock_provider, params={"date": "20240101"})

        mock_cache.write.assert_called_once()

    def test_run_does_not_use_cache_when_disabled(self):
        """验证禁用缓存时不检查/写入缓存"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.setting.use_cache = False
        mock_cache = Mock()
        mock_provider.cache = mock_cache

        with patch.object(source, "_fetch_all", return_value=pl.DataFrame({"col": [1]})):
            source.run(provider=mock_provider, params={"date": "20240101"})

        mock_cache.check.assert_not_called()
        mock_cache.write.assert_not_called()

    def test_run_does_not_write_empty_dataframe_to_cache(self):
        """验证不写入空 DataFrame 到缓存"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.setting.use_cache = True
        mock_cache = Mock()
        mock_cache.check.return_value = False
        mock_provider.cache = mock_cache

        with patch.object(source, "_fetch_all", return_value=pl.DataFrame()):
            source.run(provider=mock_provider, params={"date": "20240101"})

        mock_cache.write.assert_not_called()

    def test_run_calls_build_params(self):
        """验证调用 build_params 转换参数"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)

        mock_provider = Mock()
        mock_provider.setting.use_cache = False
        mock_cache = Mock()
        mock_provider.cache = mock_cache

        with patch.object(source, "build_params", return_value={"transformed": "params"}) as mock_build:
            with patch.object(source, "_fetch_all", return_value=pl.DataFrame({"col": [1]})):
                source.run(provider=mock_provider, params={"date": "20240101"})

        mock_build.assert_called_once_with({"date": "20240101"})


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """验证 export 返回字典"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        result = source.export()
        assert isinstance(result, dict)

    def test_export_contains_setting(self):
        """验证 export 包含 setting"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        result = source.export()
        assert "setting" in result
        assert isinstance(result["setting"], dict)

    def test_describe_returns_json_string(self):
        """验证 describe 返回 JSON 字符串"""
        setting = _create_minimal_setting()
        source = _ConcreteSource(setting=setting)
        result = source.describe()
        assert isinstance(result, str)
        assert "test_source" in result  # 验证包含 name


# ──────────────────────────────────────────────────────────────────────────────
# TestAbstractMethods
# ──────────────────────────────────────────────────────────────────────────────


class TestAbstractMethods:
    def test_base_source_has_abstractmethod_decorator(self):
        """验证 BaseSource 标记了抽象方法"""
        # 虽然不使用 ABC，但方法仍然抛出 NotImplementedError

        assert hasattr(BaseSource, "build_params")
        assert hasattr(BaseSource, "_fetch_all")

    def test_subclass_must_implement_build_params(self):
        """验证子类必须实现 build_params"""

        class _IncompleteSource1(BaseSource):
            def _fetch_all(self, provider, params):
                return pl.DataFrame()

        setting = _create_minimal_setting()
        source = _IncompleteSource1(setting=setting)
        with pytest.raises(NotImplementedError):
            source.build_params({})

    def test_subclass_must_implement_fetch_all(self):
        """验证子类必须实现 _fetch_all"""

        class _IncompleteSource2(BaseSource):
            def build_params(self, params):
                return params

        setting = _create_minimal_setting()
        source = _IncompleteSource2(setting=setting)

        mock_provider = Mock()
        with pytest.raises(NotImplementedError):
            source._fetch_all(mock_provider, {})
