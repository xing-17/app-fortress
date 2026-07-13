"""
综合测试：app.bridges.pipelines.context

覆盖范围
--------
- TestPipeContext   实例化、字段验证、ID 生成
- TestValidation    必填字段验证、destinations 非空验证
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.bridges.pipelines.context import PipeContext

# ── 测试数据准备 ──────────────────────────────────────────────────────────────


def _create_mock_provider():
    """创建符合 BaseProvider 接口的 mock 对象"""
    from app.bridges.resources.providers.base.provider import BaseProvider

    provider = Mock(spec=BaseProvider)
    provider.name = "mock_provider"
    return provider


def _create_mock_source():
    """创建符合 BaseSource 接口的 mock 对象"""
    from app.bridges.resources.sources.base.source import BaseSource

    source = Mock(spec=BaseSource)
    source.name = "mock_source"
    return source


def _create_mock_destination():
    """创建符合 BaseDestination 接口的 mock 对象"""
    from app.bridges.resources.destinations.base.destination import BaseDestination

    dest = Mock(spec=BaseDestination)
    dest.name = "mock_dest"
    return dest


# ──────────────────────────────────────────────────────────────────────────────
# TestPipeContext
# ──────────────────────────────────────────────────────────────────────────────


class TestPipeContext:
    def test_instantiation_with_required_fields(self):
        """测试使用必填字段实例化。"""
        ctx = PipeContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        assert ctx.request_id == "req_123"
        assert ctx.provider.name == "mock_provider"
        assert ctx.source.name == "mock_source"
        assert len(ctx.destinations) == 1

    def test_id_is_generated_automatically(self):
        """测试 ID 自动生成。"""
        ctx = PipeContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        assert ctx.id is not None
        assert isinstance(ctx.id, str)

    def test_id_prefix_is_pctx(self):
        """测试 ID 前缀为 pctx。"""
        ctx = PipeContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        assert ctx.id.startswith("pctx")

    def test_id_length_is_correct(self):
        """测试 ID 长度正确（prefix + separator + length）。"""
        ctx = PipeContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        # ID 格式: pctx-<10位字符>
        assert len(ctx.id) == len("pctx") + 1 + 10

    def test_params_default_is_empty_dict(self):
        """测试 params 默认为空字典。"""
        ctx = PipeContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        assert ctx.params == {}

    def test_params_can_be_set(self):
        """测试 params 可以设置。"""
        ctx = PipeContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
            params={"key": "value"},
        )
        assert ctx.params == {"key": "value"}

    def test_export_contains_all_fields(self):
        """测试 export() 包含所有字段。"""
        provider = _create_mock_provider()
        provider.export = Mock(return_value={"name": "mock_provider"})

        source = _create_mock_source()
        source.export = Mock(return_value={"name": "mock_source"})

        dest = _create_mock_destination()
        dest.export = Mock(return_value={"name": "mock_dest"})

        ctx = PipeContext(
            request_id="req_123",
            provider=provider,
            source=source,
            destinations=[dest],
            params={"key": "value"},
        )

        exported = ctx.export()
        assert "id" in exported
        assert exported["request_id"] == "req_123"
        assert "provider" in exported
        assert "source" in exported
        assert "destinations" in exported
        assert exported["params"] == {"key": "value"}


# ──────────────────────────────────────────────────────────────────────────────
# TestValidation
# ──────────────────────────────────────────────────────────────────────────────


class TestValidation:
    def test_missing_request_id_raises_error(self):
        """测试缺少 request_id 抛出错误。"""
        with pytest.raises(ValidationError):
            PipeContext(
                provider=_create_mock_provider(),
                source=_create_mock_source(),
                destinations=[_create_mock_destination()],
            )

    def test_missing_provider_raises_error(self):
        """测试缺少 provider 抛出错误。"""
        with pytest.raises(ValidationError):
            PipeContext(
                request_id="req_123",
                source=_create_mock_source(),
                destinations=[_create_mock_destination()],
            )

    def test_missing_source_raises_error(self):
        """测试缺少 source 抛出错误。"""
        with pytest.raises(ValidationError):
            PipeContext(
                request_id="req_123",
                provider=_create_mock_provider(),
                destinations=[_create_mock_destination()],
            )

    def test_missing_destinations_raises_error(self):
        """测试缺少 destinations 抛出错误。"""
        with pytest.raises(ValidationError):
            PipeContext(
                request_id="req_123",
                provider=_create_mock_provider(),
                source=_create_mock_source(),
            )

    def test_empty_destinations_list_is_allowed(self):
        """测试空 destinations 列表是允许的。"""
        ctx = PipeContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[],
        )
        assert ctx.destinations == []
