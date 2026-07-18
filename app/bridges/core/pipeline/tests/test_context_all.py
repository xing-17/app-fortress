"""
综合测试：app.bridges.core.pipeline.context

覆盖范围
--------
- TestPipelineContext   实例化、字段验证、ID 生成
- TestValidation        必填字段验证、destinations 非空验证
- TestExport            export() 和 describe() 方法
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.bridges.core.pipeline.context import PipelineContext

# ── 测试数据准备 ──────────────────────────────────────────────────────────────


def _create_mock_provider():
    """创建符合 BaseProvider 接口的 mock 对象"""
    from app.bridges.resources.providers.base.provider import BaseProvider

    # 使用 create_autospec 创建符合接口的 mock
    provider = Mock(spec=BaseProvider)
    provider.name = "mock_provider"
    provider.setting = Mock()
    provider.setting.max_threads = 1
    return provider


def _create_mock_source():
    """创建符合 BaseSource 接口的 mock 对象"""
    from app.bridges.resources.sources.base.source import BaseSource

    source = Mock(spec=BaseSource)
    source.name = "mock_source"
    source.setting = Mock()
    source.setting.provider_type = "mock_type"
    source.setting.strategy = "default"
    return source


def _create_mock_destination():
    """创建符合 BaseDestination 接口的 mock 对象"""
    from app.bridges.resources.destinations.base.destination import BaseDestination

    dest = Mock(spec=BaseDestination)
    dest.name = "mock_dest"
    return dest


# ──────────────────────────────────────────────────────────────────────────────
# TestPipelineContext
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineContext:
    def test_instantiation_with_required_fields(self):
        """测试使用必填字段实例化。"""
        ctx = PipelineContext(
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
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        assert ctx.id is not None
        assert isinstance(ctx.id, str)

    def test_id_prefix_is_pctx(self):
        """测试 ID 前缀为 pctx。"""
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        assert ctx.id.startswith("pctx")

    def test_id_length_is_correct(self):
        """测试 ID 长度正确（prefix + length）。"""
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        # ID = prefix(4) + "_" + random(10) = 15
        assert len(ctx.id) == 4 + 1 + 10

    def test_params_default_to_empty_dict(self):
        """测试 params 默认为空字典。"""
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        assert ctx.params == {}

    def test_params_can_be_provided(self):
        """测试可以提供 params。"""
        params = {"start_date": "2024-01-01", "end_date": "2024-01-31"}
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
            params=params,
        )
        assert ctx.params == params


# ──────────────────────────────────────────────────────────────────────────────
# TestValidation
# ──────────────────────────────────────────────────────────────────────────────


class TestValidation:
    def test_missing_request_id_raises_error(self):
        """测试缺少 request_id 抛出错误。"""
        with pytest.raises(ValidationError):
            PipelineContext(
                provider=_create_mock_provider(),
                source=_create_mock_source(),
                destinations=[_create_mock_destination()],
            )

    def test_missing_provider_raises_error(self):
        """测试缺少 provider 抛出错误。"""
        with pytest.raises(ValidationError):
            PipelineContext(
                request_id="req_123",
                source=_create_mock_source(),
                destinations=[_create_mock_destination()],
            )

    def test_missing_source_raises_error(self):
        """测试缺少 source 抛出错误。"""
        with pytest.raises(ValidationError):
            PipelineContext(
                request_id="req_123",
                provider=_create_mock_provider(),
                destinations=[_create_mock_destination()],
            )

    def test_missing_destinations_raises_error(self):
        """测试缺少 destinations 抛出错误。"""
        with pytest.raises(ValidationError):
            PipelineContext(
                request_id="req_123",
                provider=_create_mock_provider(),
                source=_create_mock_source(),
            )

    def test_empty_destinations_raises_error(self):
        """测试空 destinations 列表抛出错误。"""
        with pytest.raises(ValidationError):
            PipelineContext(
                request_id="req_123",
                provider=_create_mock_provider(),
                source=_create_mock_source(),
                destinations=[],
            )

    def test_multiple_destinations_accepted(self):
        """测试接受多个 destinations。"""
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[
                _create_mock_destination(),
                _create_mock_destination(),
            ],
        )
        assert len(ctx.destinations) == 2


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        result = ctx.export()
        assert isinstance(result, dict)

    def test_export_contains_request_id(self):
        """测试 export() 包含 request_id。"""
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        result = ctx.export()
        assert "request_id" in result
        assert result["request_id"] == "req_123"

    def test_export_contains_provider(self):
        """测试 export() 包含 provider。"""
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        result = ctx.export()
        assert "provider" in result

    def test_export_contains_source(self):
        """测试 export() 包含 source。"""
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        result = ctx.export()
        assert "source" in result

    def test_export_contains_destinations(self):
        """测试 export() 包含 destinations。"""
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
        )
        result = ctx.export()
        assert "destinations" in result
        assert isinstance(result["destinations"], list)

    def test_export_contains_params(self):
        """测试 export() 包含 params。"""
        ctx = PipelineContext(
            request_id="req_123",
            provider=_create_mock_provider(),
            source=_create_mock_source(),
            destinations=[_create_mock_destination()],
            params={"key": "value"},
        )
        result = ctx.export()
        assert "params" in result
        assert result["params"] == {"key": "value"}
