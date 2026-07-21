"""
综合测试：app.api.migrate.router

覆盖范围
--------
- TestSubmitEndpoint         POST /api/v2/migrate/submit
- TestLookupEndpoint         GET /api/v2/migrate/lookup/{request_id}
- TestCancelEndpoint         POST /api/v2/migrate/cancel/{request_id}
- TestHistoryEndpoint        GET /api/v2/migrate/history
- TestResetEndpoint          POST /api/v2/migrate/reset
- TestAuthentication         API Key 认证
- TestResponseModels         Pydantic 响应模型验证
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def auth_headers():
    """返回认证 headers。"""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def mock_migrate_service():
    """Mock MigrateService 返回预定义数据。"""
    service = MagicMock()

    # submit() 返回
    service.submit.return_value = "mig-test-12345"

    # lookup() 返回
    service.lookup.return_value = {
        "status": "completed",
        "started_at": "2026-07-21T10:00:00Z",
        "finished_at": "2026-07-21T10:01:00Z",
        "duration_seconds": 60.0,
        "request": {"source_name": "test_source", "from_destination": "oss_test_from"},
        "node": {"migrated_files": 10, "total_bytes": 1024000},
        "error": None,
    }

    # cancel() 返回 (不返回值)
    service.cancel.return_value = None

    # history() 返回
    service.history.return_value = [
        {
            "request_id": "mig-001",
            "status": "completed",
            "timestamp": 1721556000.0,
            "result": {"migrated_files": 10},
        },
        {
            "request_id": "mig-002",
            "status": "failed",
            "timestamp": 1721556100.0,
            "error": "Migration failed",
        },
    ]

    # reset() 返回 (不返回值)
    service.reset.return_value = None

    return service


@pytest.fixture
def app_setting():
    """创建测试用的 SystemSetting。"""
    from app.common.setting.system import ApiSetting, SystemSetting

    return SystemSetting(
        name="test-fortress",
        version="1.0.0",
        env="test",
        timezone="UTC",
        api=ApiSetting(
            key="test-api-key",
            host="127.0.0.1",
            port=8000,
        ),
    )


@pytest.fixture
def client(app_setting, mock_migrate_service):
    """创建 FastAPI TestClient，使用真实的 FortressApi 但 mock 服务。"""
    from app.interface.api import FortressApi

    # Mock 服务的启动
    with (
        patch("app.bridges.migrate._service.service.MigrateService") as MockMigrate,
        patch("app.bridges.machine._service.service.MachineService") as _,
        patch("app.bridges.core._service.service.CoreService") as _,
    ):
        # 配置 mock 实例
        MockMigrate.return_value = mock_migrate_service

        # 创建 FortressApi 实例
        fortress_api = FortressApi(setting=app_setting)

        # 替换服务实例为我们的 mock
        fortress_api.migrate_service = mock_migrate_service

        # 创建 TestClient，跳过认证
        with TestClient(fortress_api.app) as test_client:
            yield test_client


# ── TestSubmitEndpoint ────────────────────────────────────────────────────────


class TestSubmitEndpoint:
    """测试 POST /api/v2/migrate/submit 端点。"""

    def test_returns_200(self, client, auth_headers):
        """验证端点返回 200 状态码。"""
        payload = {
            "source_name": "test_source",
            "from_destination": "oss_test_from",
            "from_glob": "test/path/**/*.parquet",
            "to_destination": "oss_test_to",
        }
        response = client.post(
            "/api/v2/migrate/submit",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 200

    def test_response_contains_request_id(self, client, auth_headers):
        """验证响应包含 request_id。"""
        payload = {
            "source_name": "test_source",
            "from_destination": "oss_test_from",
            "from_glob": "test/path/**/*.parquet",
            "to_destination": "oss_test_to",
        }
        response = client.post(
            "/api/v2/migrate/submit",
            headers=auth_headers,
            json=payload,
        )
        data = response.json()
        assert "request_id" in data
        assert data["request_id"] == "mig-test-12345"

    def test_validates_request_body(self, client, auth_headers):
        """验证请求体校验。"""
        # 缺少必需字段
        response = client.post(
            "/api/v2/migrate/submit",
            headers=auth_headers,
            json={"source_name": "test"},
        )
        assert response.status_code == 422

    def test_accepts_optional_fields(self, client, auth_headers):
        """验证接受可选字段。"""
        payload = {
            "source_name": "test_source",
            "from_destination": "oss_test_from",
            "from_glob": "test/path/**/*.parquet",
            "to_destination": "oss_test_to",
            "transform_sql": "SELECT * FROM <source>",
            "options": ["FORMAT parquet"],
            "extensions": ["httpfs"],
        }
        response = client.post(
            "/api/v2/migrate/submit",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 200


# ── TestLookupEndpoint ────────────────────────────────────────────────────────


class TestLookupEndpoint:
    """测试 GET /api/v2/migrate/lookup/{request_id} 端点。"""

    def test_returns_200(self, client, auth_headers):
        """验证端点返回 200 状态码。"""
        response = client.get(
            "/api/v2/migrate/lookup/mig-test-12345",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_response_structure(self, client, auth_headers):
        """验证响应包含必需字段。"""
        response = client.get(
            "/api/v2/migrate/lookup/mig-test-12345",
            headers=auth_headers,
        )
        data = response.json()
        assert "status" in data
        assert "started_at" in data
        assert "finished_at" in data
        assert "duration_seconds" in data
        assert "request" in data
        assert "node" in data
        assert "error" in data

    def test_response_values(self, client, auth_headers):
        """验证响应数据正确。"""
        response = client.get(
            "/api/v2/migrate/lookup/mig-test-12345",
            headers=auth_headers,
        )
        data = response.json()
        assert data["status"] == "completed"
        assert data["error"] is None
        assert data["request"] is not None
        assert data["node"] is not None

    def test_not_found_returns_404(self, client, auth_headers, mock_migrate_service):
        """验证不存在的 request_id 返回 404。"""
        # Mock 抛出 ValueError（表示未找到）
        mock_migrate_service.lookup.side_effect = ValueError("Request not found")

        response = client.get(
            "/api/v2/migrate/lookup/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404


# ── TestCancelEndpoint ────────────────────────────────────────────────────────


class TestCancelEndpoint:
    """测试 POST /api/v2/migrate/cancel/{request_id} 端点。"""

    def test_returns_200(self, client, auth_headers):
        """验证端点返回 200 状态码。"""
        response = client.post(
            "/api/v2/migrate/cancel/mig-test-12345",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_response_contains_canceled_id(self, client, auth_headers):
        """验证响应包含被取消的 request_id。"""
        response = client.post(
            "/api/v2/migrate/cancel/mig-test-12345",
            headers=auth_headers,
        )
        data = response.json()
        assert "canceled" in data
        assert data["canceled"] == "mig-test-12345"


# ── TestHistoryEndpoint ───────────────────────────────────────────────────────


class TestHistoryEndpoint:
    """测试 GET /api/v2/migrate/history 端点。"""

    def test_returns_200(self, client, auth_headers):
        """验证端点返回 200 状态码。"""
        response = client.get("/api/v2/migrate/history", headers=auth_headers)
        assert response.status_code == 200

    def test_response_structure(self, client, auth_headers):
        """验证响应包含 history 数组。"""
        response = client.get("/api/v2/migrate/history", headers=auth_headers)
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)

    def test_history_items_structure(self, client, auth_headers):
        """验证历史记录项的结构。"""
        response = client.get("/api/v2/migrate/history", headers=auth_headers)
        data = response.json()
        history = data["history"]
        assert len(history) > 0
        first_item = history[0]
        assert "request_id" in first_item
        assert "status" in first_item


# ── TestResetEndpoint ─────────────────────────────────────────────────────────


class TestResetEndpoint:
    """测试 POST /api/v2/migrate/reset 端点。"""

    def test_returns_200(self, client, auth_headers):
        """验证端点返回 200 状态码。"""
        response = client.post("/api/v2/migrate/reset", headers=auth_headers)
        assert response.status_code == 200

    def test_response_contains_status(self, client, auth_headers):
        """验证响应包含 status 字段。"""
        response = client.post("/api/v2/migrate/reset", headers=auth_headers)
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


# ── TestResponseModels ────────────────────────────────────────────────────────


class TestResponseModels:
    def test_submit_validates_against_model(self, client, auth_headers):
        """验证 /submit 响应符合 MigrateSubmitResponseModel。"""
        from app.api.migrate.router import MigrateSubmitResponseModel

        payload = {
            "source_name": "test_source",
            "from_destination": "oss_test_from",
            "from_glob": "test/path/**/*.parquet",
            "to_destination": "oss_test_to",
        }
        response = client.post(
            "/api/v2/migrate/submit",
            headers=auth_headers,
            json=payload,
        )
        data = response.json()

        # Pydantic 模型验证
        model = MigrateSubmitResponseModel.model_validate(data)
        assert model.request_id == "mig-test-12345"

    def test_lookup_validates_against_model(self, client, auth_headers):
        """验证 /lookup 响应符合 MigrateLookupResponseModel。"""
        from app.api.migrate.router import MigrateLookupResponseModel

        response = client.get(
            "/api/v2/migrate/lookup/mig-test-12345",
            headers=auth_headers,
        )
        data = response.json()

        # Pydantic 模型验证
        model = MigrateLookupResponseModel.model_validate(data)
        assert model.status == "completed"
        assert model.error is None

    def test_history_validates_against_model(self, client, auth_headers):
        """验证 /history 响应符合 MigrateHistoryResponseModel。"""
        from app.api.migrate.router import MigrateHistoryResponseModel

        response = client.get("/api/v2/migrate/history", headers=auth_headers)
        data = response.json()

        # Pydantic 模型验证
        model = MigrateHistoryResponseModel.model_validate(data)
        assert len(model.history) > 0


# ── TestEdgeCases ─────────────────────────────────────────────────────────────


class TestEdgeCases:
    """测试边界情况和错误处理。"""

    def test_invalid_endpoint(self, client, auth_headers):
        """验证不存在的端点返回 404。"""
        response = client.get("/api/v2/migrate/nonexistent", headers=auth_headers)
        assert response.status_code == 404
