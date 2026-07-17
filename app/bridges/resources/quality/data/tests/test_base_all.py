"""
综合测试：app.bridges.resources.quality.data.base

覆盖范围
--------
- TestBaseDataQualityAbstract    抽象基类特性测试
- TestBaseDataQualityDescribe    describe() 方法测试
- TestBaseDataQualitySubclass    子类实现验证
"""

from __future__ import annotations

import json
from typing import Any

import polars as pl
import pytest

from app.bridges.resources.quality.data.base import BaseDataQuality

# ──────────────────────────────────────────────────────────────────────────────
# TestBaseDataQualityAbstract
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseDataQualityAbstract:
    def test_cannot_instantiate_abstract_class(self):
        """测试抽象基类不能直接实例化。"""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseDataQuality()  # type: ignore

    def test_abstract_methods_exist(self):
        """测试抽象方法是否正确定义。"""
        abstract_methods = BaseDataQuality.__abstractmethods__
        assert "get_category" in abstract_methods
        assert "get_identifier" in abstract_methods
        assert "report" in abstract_methods
        assert "export" in abstract_methods

    def test_subclass_without_implementation_raises_error(self):
        """测试不实现抽象方法的子类无法实例化。"""

        class IncompleteQuality(BaseDataQuality):
            """未实现所有抽象方法的子类。"""

            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteQuality()  # type: ignore

    def test_partial_implementation_raises_error(self):
        """测试只实现部分抽象方法的子类无法实例化。"""

        class PartialQuality(BaseDataQuality):
            """只实现部分抽象方法的子类。"""

            def get_category(self) -> str:
                return "test"

            def get_identifier(self) -> str:
                return "test_id"

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PartialQuality()  # type: ignore


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseDataQualityDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseDataQualityDescribe:
    def test_describe_calls_export(self):
        """测试 describe() 方法调用 export() 并返回 JSON。"""

        class MinimalQuality(BaseDataQuality):
            """最小实现子类用于测试。"""

            def get_category(self) -> str:
                return "test_category"

            def get_identifier(self) -> str:
                return "test_id_123"

            def report(self) -> pl.DataFrame:
                return pl.DataFrame({"col": [1, 2, 3]})

            def export(self) -> dict[str, Any]:
                return {
                    "category": self.get_category(),
                    "identifier": self.get_identifier(),
                    "test": "value",
                }

        quality = MinimalQuality()
        result = quality.describe()

        # 验证返回的是字符串
        assert isinstance(result, str)

        # 验证是有效的 JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert parsed["category"] == "test_category"
        assert parsed["identifier"] == "test_id_123"
        assert parsed["test"] == "value"

    def test_describe_formats_json_with_indent(self):
        """测试 describe() 返回格式化的 JSON（带缩进）。"""

        class FormattedQuality(BaseDataQuality):
            """用于测试 JSON 格式化的子类。"""

            def get_category(self) -> str:
                return "formatted"

            def get_identifier(self) -> str:
                return "fmt_001"

            def report(self) -> pl.DataFrame:
                return pl.DataFrame()

            def export(self) -> dict[str, Any]:
                return {"key1": "value1", "key2": "value2", "nested": {"inner": "data"}}

        quality = FormattedQuality()
        result = quality.describe()

        # 验证包含缩进（格式化后的 JSON 会包含多行）
        assert "\n" in result
        assert "    " in result  # 4 空格缩进

        # 验证内容正确
        parsed = json.loads(result)
        assert parsed["key1"] == "value1"
        assert parsed["nested"]["inner"] == "data"

    def test_describe_supports_chinese_characters(self):
        """测试 describe() 支持中文字符（ensure_ascii=False）。"""

        class ChineseQuality(BaseDataQuality):
            """包含中文数据的子类。"""

            def get_category(self) -> str:
                return "中文类别"

            def get_identifier(self) -> str:
                return "标识符_001"

            def report(self) -> pl.DataFrame:
                return pl.DataFrame()

            def export(self) -> dict[str, Any]:
                return {
                    "名称": "测试数据",
                    "描述": "这是一个测试",
                    "状态": "完成",
                }

        quality = ChineseQuality()
        result = quality.describe()

        # 验证返回的是有效 JSON 并且包含中文内容
        parsed = json.loads(result)
        assert parsed["名称"] == "测试数据"
        assert parsed["描述"] == "这是一个测试"
        assert parsed["状态"] == "完成"

    def test_describe_handles_empty_export(self):
        """测试 describe() 处理空的 export() 返回。"""

        class EmptyExportQuality(BaseDataQuality):
            """返回空字典的子类。"""

            def get_category(self) -> str:
                return "empty"

            def get_identifier(self) -> str:
                return "empty_001"

            def report(self) -> pl.DataFrame:
                return pl.DataFrame()

            def export(self) -> dict[str, Any]:
                return {}

        quality = EmptyExportQuality()
        result = quality.describe()

        assert result == "{}"

    def test_describe_handles_complex_nested_data(self):
        """测试 describe() 处理复杂嵌套数据。"""

        class ComplexQuality(BaseDataQuality):
            """包含复杂嵌套数据的子类。"""

            def get_category(self) -> str:
                return "complex"

            def get_identifier(self) -> str:
                return "complex_001"

            def report(self) -> pl.DataFrame:
                return pl.DataFrame()

            def export(self) -> dict[str, Any]:
                return {
                    "metadata": {
                        "source": "test",
                        "version": "1.0",
                    },
                    "metrics": {
                        "count": 100,
                        "rates": [0.1, 0.2, 0.3],
                    },
                    "flags": [True, False, True],
                }

        quality = ComplexQuality()
        result = quality.describe()

        parsed = json.loads(result)
        assert parsed["metadata"]["source"] == "test"
        assert parsed["metrics"]["rates"] == [0.1, 0.2, 0.3]
        assert parsed["flags"] == [True, False, True]


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseDataQualitySubclass
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseDataQualitySubclass:
    def test_complete_implementation_works(self):
        """测试完整实现所有抽象方法的子类可以正常实例化。"""

        class CompleteQuality(BaseDataQuality):
            """完整实现所有抽象方法的子类。"""

            def __init__(self, category: str, identifier: str):
                self.category = category
                self.identifier = identifier

            def get_category(self) -> str:
                return self.category

            def get_identifier(self) -> str:
                return self.identifier

            def report(self) -> pl.DataFrame:
                return pl.DataFrame(
                    {
                        "category": [self.category],
                        "identifier": [self.identifier],
                    }
                )

            def export(self) -> dict[str, Any]:
                return {
                    "category": self.category,
                    "identifier": self.identifier,
                }

        # 应该能够成功实例化
        quality = CompleteQuality(category="test", identifier="test_001")
        assert quality.get_category() == "test"
        assert quality.get_identifier() == "test_001"

    def test_subclass_can_add_additional_methods(self):
        """测试子类可以添加额外的方法。"""

        class ExtendedQuality(BaseDataQuality):
            """添加了额外方法的子类。"""

            def get_category(self) -> str:
                return "extended"

            def get_identifier(self) -> str:
                return "ext_001"

            def report(self) -> pl.DataFrame:
                return pl.DataFrame()

            def export(self) -> dict[str, Any]:
                return {"extra_field": self.get_extra()}

            def get_extra(self) -> str:
                """额外的自定义方法。"""
                return "extra_value"

        quality = ExtendedQuality()
        assert quality.get_extra() == "extra_value"
        assert quality.export()["extra_field"] == "extra_value"

    def test_subclass_can_override_describe(self):
        """测试子类可以覆盖 describe() 方法。"""

        class CustomDescribeQuality(BaseDataQuality):
            """覆盖 describe() 方法的子类。"""

            def get_category(self) -> str:
                return "custom"

            def get_identifier(self) -> str:
                return "custom_001"

            def report(self) -> pl.DataFrame:
                return pl.DataFrame()

            def export(self) -> dict[str, Any]:
                return {"data": "value"}

            def describe(self) -> str:
                """自定义的 describe() 实现。"""
                return "CUSTOM: " + super().describe()

        quality = CustomDescribeQuality()
        result = quality.describe()

        assert result.startswith("CUSTOM: ")
        assert '"data"' in result
        assert '"value"' in result

    def test_multiple_subclasses_independence(self):
        """测试多个子类之间相互独立。"""

        class QualityA(BaseDataQuality):
            def get_category(self) -> str:
                return "A"

            def get_identifier(self) -> str:
                return "a_001"

            def report(self) -> pl.DataFrame:
                return pl.DataFrame({"type": ["A"]})

            def export(self) -> dict[str, Any]:
                return {"type": "A"}

        class QualityB(BaseDataQuality):
            def get_category(self) -> str:
                return "B"

            def get_identifier(self) -> str:
                return "b_001"

            def report(self) -> pl.DataFrame:
                return pl.DataFrame({"type": ["B"]})

            def export(self) -> dict[str, Any]:
                return {"type": "B"}

        quality_a = QualityA()
        quality_b = QualityB()

        assert quality_a.get_category() == "A"
        assert quality_b.get_category() == "B"
        assert quality_a.get_identifier() == "a_001"
        assert quality_b.get_identifier() == "b_001"
