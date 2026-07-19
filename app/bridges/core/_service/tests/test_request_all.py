"""
综合测试：app.bridges.core._service.request

覆盖范围
--------
- TestCoreRequest       实例化、字段验证、ID 生成
- TestExport            export() 和 describe() 方法
"""

from __future__ import annotations

import json

from app.bridges.core._service.request import CoreRequest

# ──────────────────────────────────────────────────────────────────────────────
# TestCoreRequest
# ──────────────────────────────────────────────────────────────────────────────


class TestCoreRequest:
    def test_instantiation_with_defaults(self):
        """测试使用默认值实例化。"""
        req = CoreRequest()
        assert req.providers == {}
        assert req.sources_by_tags == {}
        assert req.params == {}
        assert req.destinations == []

    def test_instantiation_with_fields(self):
        """测试使用字段值实例化。"""
        req = CoreRequest(
            providers={"tushare": "tushare_prod"},
            sources_by_tags={"region": "us", "type": "stock"},
            params={"start_date": "2023-01-01"},
            destinations=["file", "database"],
        )
        assert req.providers == {"tushare": "tushare_prod"}
        assert req.sources_by_tags == {"region": "us", "type": "stock"}
        assert req.params == {"start_date": "2023-01-01"}
        assert req.destinations == ["file", "database"]

    def test_id_is_generated_automatically(self):
        """测试 ID 自动生成。"""
        req = CoreRequest()
        assert req.id is not None
        assert isinstance(req.id, str)

    def test_id_prefix_is_req(self):
        """测试 ID 前缀为 req。"""
        req = CoreRequest()
        assert req.id.startswith("req")

    def test_id_length_is_correct(self):
        """测试 ID 长度正确（prefix + '-' + length）。"""
        req = CoreRequest()
        # id_prefix="req"(3) + "-"(1) + id_length=8 = 12
        assert len(req.id) == 3 + 1 + 8

    def test_two_requests_have_different_ids(self):
        """测试两个请求有不同的 ID。"""
        req1 = CoreRequest()
        req2 = CoreRequest()
        assert req1.id != req2.id

    def test_created_at_is_set(self):
        """测试 created_at 自动设置。"""
        req = CoreRequest()
        assert req.created_at is not None

    def test_category_is_class_name(self):
        """测试 category 为类名。"""
        req = CoreRequest()
        assert req.category == "CoreRequest"


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_contains_providers(self):
        """测试 export() 包含 providers 字段。"""
        req = CoreRequest(providers={"tushare": "tushare_prod"})
        result = req.export()
        assert result["providers"] == {"tushare": "tushare_prod"}

    def test_export_contains_sources_by_tags(self):
        """测试 export() 包含 sources_by_tags 字段。"""
        req = CoreRequest(sources_by_tags={"region": "us"})
        result = req.export()
        assert result["sources_by_tags"] == {"region": "us"}

    def test_export_contains_params(self):
        """测试 export() 包含 params 字段。"""
        req = CoreRequest(params={"start_date": "2023-01-01"})
        result = req.export()
        assert result["params"] == {"start_date": "2023-01-01"}

    def test_export_contains_destinations(self):
        """测试 export() 包含 destinations 字段。"""
        req = CoreRequest(destinations=["file"])
        result = req.export()
        assert result["destinations"] == ["file"]

    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        req = CoreRequest()
        result = req.export()
        assert isinstance(result, dict)

    def test_describe_returns_valid_json(self):
        """测试 describe() 返回有效 JSON 字符串。"""
        req = CoreRequest()
        result = req.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_contains_providers(self):
        """测试 describe() 包含 providers 数据。"""
        req = CoreRequest(providers={"tushare": "tushare_prod"})
        result = json.loads(req.describe())
        assert result["providers"] == {"tushare": "tushare_prod"}
