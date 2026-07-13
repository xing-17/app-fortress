"""
综合测试：app.bridges.core.request

覆盖范围
--------
- TestBridgesRequest         基本实例化、字段验证
- TestRequestID              ID 生成和前缀验证
- TestRequestExport          export() 和 describe() 方法
"""

from __future__ import annotations

import json

from app.bridges.core.request import BridgesRequest

# ──────────────────────────────────────────────────────────────────────────────
# TestBridgesRequest
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgesRequest:
    def test_create_empty_request(self):
        """测试创建空请求。"""
        request = BridgesRequest()
        assert request.providers == {}
        assert request.sources_by_tags == {}
        assert request.params == {}
        assert request.destinations == []

    def test_create_request_with_providers(self):
        """测试创建带 providers 的请求。"""
        request = BridgesRequest(providers={"tushare": "tushare_prod"})
        assert request.providers == {"tushare": "tushare_prod"}

    def test_create_request_with_sources_by_tags(self):
        """测试创建带 sources_by_tags 的请求。"""
        request = BridgesRequest(sources_by_tags={"region": "us", "type": "stock"})
        assert request.sources_by_tags == {"region": "us", "type": "stock"}

    def test_create_request_with_params(self):
        """测试创建带 params 的请求。"""
        request = BridgesRequest(params={"start_date": "2023-01-01", "end_date": "2023-12-31"})
        assert request.params == {"start_date": "2023-01-01", "end_date": "2023-12-31"}

    def test_create_request_with_destinations(self):
        """测试创建带 destinations 的请求。"""
        request = BridgesRequest(destinations=["file", "database"])
        assert request.destinations == ["file", "database"]

    def test_create_full_request(self):
        """测试创建完整请求。"""
        request = BridgesRequest(
            providers={"tushare": "tushare_prod"},
            sources_by_tags={"region": "cn", "type": "stock"},
            params={"start_date": "2023-01-01"},
            destinations=["file"],
        )
        assert request.providers == {"tushare": "tushare_prod"}
        assert request.sources_by_tags == {"region": "cn", "type": "stock"}
        assert request.params == {"start_date": "2023-01-01"}
        assert request.destinations == ["file"]


# ──────────────────────────────────────────────────────────────────────────────
# TestRequestID
# ──────────────────────────────────────────────────────────────────────────────


class TestRequestID:
    def test_id_is_generated(self):
        """测试 ID 自动生成。"""
        request = BridgesRequest()
        assert request.id is not None
        assert len(request.id) > 0

    def test_id_has_prefix(self):
        """测试 ID 包含前缀。"""
        request = BridgesRequest()
        assert request.id.startswith("req-")

    def test_id_length(self):
        """测试 ID 长度正确（prefix + '-' + 8字符）。"""
        request = BridgesRequest()
        # id_prefix = "req" (3) + "-" (1) + id_length (8) = 12
        assert len(request.id) == 12

    def test_different_requests_have_different_ids(self):
        """测试不同请求有不同的 ID。"""
        request1 = BridgesRequest()
        request2 = BridgesRequest()
        assert request1.id != request2.id


# ──────────────────────────────────────────────────────────────────────────────
# TestRequestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestRequestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        request = BridgesRequest()
        result = request.export()
        assert isinstance(result, dict)

    def test_export_contains_id(self):
        """测试导出包含 ID。"""
        request = BridgesRequest()
        result = request.export()
        assert "id" in result
        assert result["id"] == request.id

    def test_export_contains_all_fields(self):
        """测试导出包含所有字段。"""
        request = BridgesRequest(
            providers={"tushare": "prod"},
            sources_by_tags={"region": "cn"},
            params={"date": "2023-01-01"},
            destinations=["file"],
        )
        result = request.export()
        assert result["providers"] == {"tushare": "prod"}
        assert result["sources_by_tags"] == {"region": "cn"}
        assert result["params"] == {"date": "2023-01-01"}
        assert result["destinations"] == ["file"]

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        request = BridgesRequest()
        result = request.describe()
        assert isinstance(result, str)
        # 验证可以解析为 JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_contains_same_data_as_export(self):
        """测试 describe() 包含与 export() 相同的数据。"""
        request = BridgesRequest(
            providers={"tushare": "prod"},
            destinations=["file"],
        )
        exported = request.export()
        described = json.loads(request.describe())
        assert exported == described
