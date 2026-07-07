"""
综合测试：app.common.context.base

覆盖范围
--------
- TestCategory     category 返回类名；子类返回子类名；包含在 export 中
- TestCreatedAt    自动设置为当前时间；时区感知；frozen 不可修改；手动设置保留
- TestFromAny      从 dict 创建；从 JSON 字符串创建；无效 JSON 抛异常；无效类型抛异常
- TestExport       export() 返回 dict；包含所有字段（含 category 和 created_at）
- TestDescribe     describe() 返回 JSON 字符串；与 export() 值一致
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.common.context.base import BaseContext

# ── 测试用具体子类 ────────────────────────────────────────────────────────────


class _SimpleContext(BaseContext):
    name: str
    value: int = 0


class _ChildContext(_SimpleContext):
    extra: str = "child"


# ──────────────────────────────────────────────────────────────────────────────
# TestCategory
# ──────────────────────────────────────────────────────────────────────────────


class TestCategory:
    def test_base_subclass_category_equals_classname(self):
        """测试子类的 category 等于类名。"""
        obj = _SimpleContext(name="x")
        assert obj.category == "_SimpleContext"

    def test_child_category_equals_child_classname(self):
        """测试子类的子类的 category 等于其类名。"""
        obj = _ChildContext(name="x")
        assert obj.category == "_ChildContext"

    def test_category_included_in_export(self):
        """测试 category 包含在 export() 结果中。"""
        obj = _SimpleContext(name="x")
        assert "category" in obj.export()

    def test_category_value_matches_classname(self):
        """测试 export() 中的 category 值与类名匹配。"""
        obj = _SimpleContext(name="abc")
        assert obj.export()["category"] == "_SimpleContext"


# ──────────────────────────────────────────────────────────────────────────────
# TestCreatedAt
# ──────────────────────────────────────────────────────────────────────────────


class TestCreatedAt:
    def test_created_at_auto_set_when_none(self):
        """测试 created_at 在未提供时自动设置。"""
        obj = _SimpleContext(name="x")
        assert obj.created_at is not None

    def test_created_at_is_datetime(self):
        """测试 created_at 是 datetime 对象。"""
        obj = _SimpleContext(name="x")
        assert isinstance(obj.created_at, datetime)

    def test_created_at_is_timezone_aware(self):
        """测试 created_at 是时区感知的。"""
        obj = _SimpleContext(name="x")
        assert obj.created_at.tzinfo is not None

    def test_created_at_is_recent(self):
        """测试 created_at 是最近的时间（在过去 1 秒内）。"""
        obj = _SimpleContext(name="x")
        now = obj._get_current_datetime()
        delta = (now - obj.created_at).total_seconds()
        assert 0 <= delta < 1

    def test_created_at_preserved_when_provided(self):
        """测试手动提供 created_at 时保留原值。"""
        temp_obj = _SimpleContext(name="temp")
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=temp_obj.created_at.tzinfo)
        obj = _SimpleContext(name="x", created_at=custom_time)
        assert obj.created_at == custom_time

    def test_created_at_is_frozen(self):
        """测试 created_at 是 frozen 字段，不可修改。"""
        obj = _SimpleContext(name="x")
        with pytest.raises(ValidationError, match="frozen"):
            obj.created_at = datetime.now()

    def test_created_at_included_in_export(self):
        """测试 created_at 包含在 export() 结果中。"""
        obj = _SimpleContext(name="x")
        exported = obj.export()
        assert "created_at" in exported
        assert isinstance(exported["created_at"], str)


# ──────────────────────────────────────────────────────────────────────────────
# TestFromAny
# ──────────────────────────────────────────────────────────────────────────────


class TestFromAny:
    def test_from_dict_returns_instance(self):
        """测试从字典创建实例。"""
        data = {"name": "test", "value": 42}
        obj = _SimpleContext.from_any(data)
        assert isinstance(obj, _SimpleContext)

    def test_from_dict_populates_fields(self):
        """测试从字典创建时字段值正确。"""
        data = {"name": "test", "value": 42}
        obj = _SimpleContext.from_any(data)
        assert obj.name == "test"
        assert obj.value == 42

    def test_from_json_string_returns_instance(self):
        """测试从 JSON 字符串创建实例。"""
        json_str = '{"name": "test", "value": 42}'
        obj = _SimpleContext.from_any(json_str)
        assert isinstance(obj, _SimpleContext)

    def test_from_json_string_populates_fields(self):
        """测试从 JSON 字符串创建时字段值正确。"""
        json_str = '{"name": "test", "value": 42}'
        obj = _SimpleContext.from_any(json_str)
        assert obj.name == "test"
        assert obj.value == 42

    def test_invalid_json_string_raises_valueerror(self):
        """测试无效 JSON 字符串抛出 ValueError。"""
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            _SimpleContext.from_any('{"name": invalid}')

    def test_invalid_type_raises_valueerror(self):
        """测试无效类型（非 str/dict）抛出 ValueError。"""
        with pytest.raises(ValueError, match="Invalid type for context"):
            _SimpleContext.from_any(123)

    def test_invalid_type_list_raises_valueerror(self):
        """测试列表类型抛出 ValueError。"""
        with pytest.raises(ValueError, match="Invalid type for context"):
            _SimpleContext.from_any([1, 2, 3])

    def test_missing_required_field_raises_validationerror(self):
        """测试缺少必需字段时抛出 ValidationError。"""
        with pytest.raises(ValidationError):
            _SimpleContext.from_any({"value": 42})

    def test_from_json_with_created_at(self):
        """测试从 JSON 创建时可以指定 created_at。"""
        json_str = '{"name": "test", "created_at": "2024-01-01T12:00:00+00:00"}'
        obj = _SimpleContext.from_any(json_str)
        assert obj.name == "test"
        assert obj.created_at is not None


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        obj = _SimpleContext(name="x")
        assert isinstance(obj.export(), dict)

    def test_export_contains_all_fields(self):
        """测试 export() 包含所有字段。"""
        obj = _SimpleContext(name="test", value=42)
        data = obj.export()
        assert data["name"] == "test"
        assert data["value"] == 42
        assert data["category"] == "_SimpleContext"
        assert "created_at" in data

    def test_export_category_is_classname(self):
        """测试 export() 中的 category 是类名。"""
        obj = _SimpleContext(name="x")
        assert obj.export()["category"] == "_SimpleContext"

    def test_export_created_at_is_iso_string(self):
        """测试 export() 中的 created_at 是 ISO 格式字符串。"""
        obj = _SimpleContext(name="x")
        exported_time = obj.export()["created_at"]
        assert isinstance(exported_time, str)
        # 验证可以解析为 datetime
        parsed = datetime.fromisoformat(exported_time)
        assert isinstance(parsed, datetime)


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_describe_returns_string(self):
        """测试 describe() 返回字符串。"""
        obj = _SimpleContext(name="x")
        assert isinstance(obj.describe(), str)

    def test_describe_is_valid_json(self):
        """测试 describe() 返回合法的 JSON 字符串。"""
        obj = _SimpleContext(name="x")
        raw = obj.describe()
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_describe_contains_all_fields(self):
        """测试 describe() 包含所有字段。"""
        obj = _SimpleContext(name="test", value=42)
        parsed = json.loads(obj.describe())
        assert "name" in parsed
        assert "value" in parsed
        assert "category" in parsed
        assert "created_at" in parsed

    def test_describe_values_match_fields(self):
        """测试 describe() 中的值与字段匹配。"""
        obj = _SimpleContext(name="test", value=42)
        parsed = json.loads(obj.describe())
        assert parsed["name"] == "test"
        assert parsed["value"] == 42
        assert parsed["category"] == "_SimpleContext"
