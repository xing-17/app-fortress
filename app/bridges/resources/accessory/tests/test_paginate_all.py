"""
综合测试：app.bridges.resources.accessory.paginate

覆盖范围
--------
- TestResolveInt       _resolve_int() None 默认值、int 校验、负值与非法值抛异常
- TestInitialization   初始化参数的正确设置
- TestReset            reset() 重置 offset 和 _count
- TestNext             next() 翻页逻辑与 offset 更新
- TestContextManager   __enter__ / __exit__ 上下文管理协议
- TestExport           export() 包含必要键且值与实例属性一致
"""

from __future__ import annotations

import pytest

from app.bridges.resources.accessory.paginate import Paginate

# ──────────────────────────────────────────────────────────────────────────────
# TestResolveInt
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveInt:
    def test_none_returns_default(self):
        p = Paginate()
        assert p.page_size == 2000
        assert p.max_pages == 10
        assert p.offset == 0

    def test_int_is_stored(self):
        p = Paginate(page_size=100, max_pages=5, offset=10)
        assert p.page_size == 100
        assert p.max_pages == 5
        assert p.offset == 10

    def test_zero_is_allowed(self):
        p = Paginate(page_size=0, max_pages=0, offset=0)
        assert p.page_size == 0
        assert p.max_pages == 0
        assert p.offset == 0

    def test_negative_page_size_raises(self):
        with pytest.raises(ValueError, match="page_size"):
            Paginate(page_size=-100)

    def test_negative_max_pages_raises(self):
        with pytest.raises(ValueError, match="max_pages"):
            Paginate(max_pages=-5)

    def test_negative_offset_raises(self):
        with pytest.raises(ValueError, match="offset"):
            Paginate(offset=-10)

    def test_float_page_size_raises(self):
        with pytest.raises(ValueError, match="page_size"):
            Paginate(page_size=100.5)

    def test_string_value_raises(self):
        with pytest.raises(ValueError):
            Paginate(page_size="large")


# ──────────────────────────────────────────────────────────────────────────────
# TestInitialization
# ──────────────────────────────────────────────────────────────────────────────


class TestInitialization:
    def test_default_values(self):
        p = Paginate()
        assert p.page_size == 2000
        assert p.max_pages == 10
        assert p.offset == 0
        assert p._count == 0

    def test_custom_values(self):
        p = Paginate(page_size=500, max_pages=20, offset=100)
        assert p.page_size == 500
        assert p.max_pages == 20
        assert p.offset == 100
        assert p._count == 0


# ──────────────────────────────────────────────────────────────────────────────
# TestReset
# ──────────────────────────────────────────────────────────────────────────────


class TestReset:
    def test_reset_restores_initial_offset(self):
        p = Paginate(page_size=100, offset=0)
        p.next()
        p.next()
        assert p.offset == 200
        p.reset()
        assert p.offset == 0

    def test_reset_works_after_next_calls(self):
        """验证 reset 可以在 next 调用后重置 offset"""
        p = Paginate(page_size=100)
        p.next()
        p.next()
        assert p.offset == 200
        p.reset()
        assert p.offset == 0


# ──────────────────────────────────────────────────────────────────────────────
# TestNext
# ──────────────────────────────────────────────────────────────────────────────


class TestNext:
    def test_next_increments_offset_by_page_size(self):
        p = Paginate(page_size=100, offset=0)
        result = p.next()
        assert result == (0, 100)  # 返回 (current_offset, page_size)
        assert p.offset == 100

    def test_next_multiple_calls(self):
        p = Paginate(page_size=50, offset=0)
        p.next()
        assert p.offset == 50
        p.next()
        assert p.offset == 100
        p.next()
        assert p.offset == 150

    def test_next_updates_offset_correctly(self):
        """验证 next 正确更新 offset"""
        p = Paginate(page_size=100)
        assert p.offset == 0
        p.next()
        assert p.offset == 100
        p.next()
        assert p.offset == 200

    def test_next_returns_tuple_of_offset_and_page_size(self):
        """验证 next 返回 (current_offset, page_size) 元组"""
        p = Paginate(page_size=100, offset=0)
        result1 = p.next()
        result2 = p.next()
        result3 = p.next()
        assert result1 == (0, 100)
        assert result2 == (100, 100)
        assert result3 == (200, 100)


# ──────────────────────────────────────────────────────────────────────────────
# TestContextManager
# ──────────────────────────────────────────────────────────────────────────────


class TestContextManager:
    def test_enter_returns_self(self):
        p = Paginate(page_size=100)
        with p as context:
            assert context is p

    def test_exit_returns_false(self):
        p = Paginate(page_size=100)
        result = p.__exit__(None, None, None)
        assert result is False

    def test_context_manager_works(self):
        """验证上下文管理器协议可以正常使用"""
        with Paginate(page_size=100) as p:
            assert isinstance(p, Paginate)
            p.next()
            assert p.offset == 100


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_contains_required_keys(self):
        p = Paginate(page_size=100, max_pages=5, offset=50)
        result = p.export()
        assert {"page_size", "max_pages", "offset"}.issubset(result)

    def test_export_includes_base_klass_key(self):
        p = Paginate()
        assert "klass" in p.export()

    def test_export_values_match_attributes(self):
        p = Paginate(page_size=500, max_pages=20, offset=100)
        result = p.export()
        assert result["page_size"] == p.page_size
        assert result["max_pages"] == p.max_pages
        assert result["offset"] == p.offset

    def test_export_default_values(self):
        p = Paginate()
        result = p.export()
        assert result["page_size"] == 2000
        assert result["max_pages"] == 10
        assert result["offset"] == 0
