"""
综合测试：app.api.machine.router

覆盖范围
--------
- TestCheckEndpoint          GET /api/v2/machine/check
- TestCurrentEndpoint        GET /api/v2/machine/current
- TestHistoryEndpoint        GET /api/v2/machine/history
- TestServiceHealthEndpoint  GET /api/v2/machine/servicehealth
- TestAuthentication         API Key 认证
- TestResponseModels         Pydantic 响应模型验证
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.bridges.base.servicehealth import ServiceHealth

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def auth_headers():
    """返回认证 headers。"""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def mock_machine_service():
    """Mock MachineService 返回预定义数据。"""
    service = MagicMock()

    # check() 返回
    service.check.return_value = {
        "status": "ok",
        "name": "test-fortress",
        "version": "1.0.0",
        "env": "test",
        "timezone": "UTC",
    }

    # current() 返回
    service.current.return_value = {
        "id": "macs-test123",
        "created_at": "2026-07-21T10:00:00",
        "timestamp": 1721556000.0,
        "cpu_percent": 12.5,
        "mem_percent": 68.2,
        "mem_used_mb": 8192,
        "mem_total_mb": 12000,
        "swap_percent": 5.0,
        "disk_percent": 45.3,
        "disk_used_mb": 256000,
        "disk_total_mb": 565000,
        "proc_mem_mb": 512,
        "proc_mem_percent": 4.27,
        "proc_cpu_percent": 2.5,
        "proc_workers": 8,
        "net_sent_mb": 1024,
        "net_recv_mb": 2048,
    }

    # history() 返回
    service.history.return_value = [
        service.current.return_value,
        {**service.current.return_value, "timestamp": 1721556060.0},
    ]

    # health() 返回
    service.health.return_value = ServiceHealth(
        service="machine",
        worker_name="machine-worker",
        worker_alive=True,
        worker_daemon=True,
        worker_ident=12345,
        worker_count=3,
        last_active_time=1000.0,
    )

    return service


@pytest.fixture
def mock_core_service():
    """Mock CoreService。"""
    service = MagicMock()
    service.health.return_value = ServiceHealth(
        service="core",
        worker_name="core-worker",
        worker_alive=True,
        worker_daemon=True,
        worker_ident=12346,
        worker_count=2,
        last_active_time=1001.0,
    )
    return service


@pytest.fixture
def mock_migrate_service():
    """Mock MigrateService。"""
    service = MagicMock()
    service.health.return_value = ServiceHealth(
        service="migrate",
        worker_name="migrate-worker",
        worker_alive=True,
        worker_daemon=True,
        worker_ident=12347,
        worker_count=2,
        last_active_time=1002.0,
    )
    return service


@pytest.fixture
def api_setting():
    """创建测试用的 ApiSetting。"""
    from app.common.setting.api import ApiSetting

    return ApiSetting(
        version="1.0.0",
        key="test-api-key",
        host="127.0.0.1",
        port=8000,
    )


@pytest.fixture
def client(api_setting, mock_machine_service, mock_core_service, mock_migrate_service):
    """创建 FastAPI TestClient，使用真实的 FortressApi 但 mock 服务。"""
    from app.api.app import FortressApi

    # Mock 服务的启动
    with (
        patch("app.bridges.machine._service.service.MachineService") as MockMachine,
        patch("app.bridges.core._service.service.CoreService") as MockCore,
        patch("app.bridges.migrate._service.service.MigrateService") as MockMigrate,
    ):
        # 配置 mock 实例
        MockMachine.return_value = mock_machine_service
        MockCore.return_value = mock_core_service
        MockMigrate.return_value = mock_migrate_service

        # 创建 FortressApi 实例
        fortress_api = FortressApi(setting=api_setting)

        # 替换服务实例为我们的 mock
        fortress_api.machine_service = mock_machine_service
        fortress_api.core_service = mock_core_service
        fortress_api.migrate_service = mock_migrate_service

        # 创建 TestClient，跳过认证
        with TestClient(fortress_api.app) as test_client:
            yield test_client


# ── TestCheckEndpoint ─────────────────────────────────────────────────────────


class TestCheckEndpoint:
    """测试 GET /api/v2/machine/check 端点。"""

    def test_returns_200(self, client, auth_headers):
        """验证端点返回 200 状态码。"""
        response = client.get("/api/v2/machine/check", headers=auth_headers)
        assert response.status_code == 200

    def test_response_structure(self, client, auth_headers):
        """验证响应包含必需字段。"""
        response = client.get("/api/v2/machine/check", headers=auth_headers)
        data = response.json()
        assert "status" in data
        assert "name" in data
        assert "version" in data

    def test_response_values(self, client, auth_headers):
        """验证响应数据正确。"""
        response = client.get("/api/v2/machine/check", headers=auth_headers)
        data = response.json()
        assert data["status"] == "ok"
        assert data["name"] == "test-fortress"
        assert data["version"] == "1.0.0"


# ── TestCurrentEndpoint ───────────────────────────────────────────────────────


class TestCurrentEndpoint:
    """测试 GET /api/v2/machine/current 端点。"""

    def test_returns_200(self, client, auth_headers):
        """验证端点返回 200 状态码。"""
        response = client.get("/api/v2/machine/current", headers=auth_headers)
        assert response.status_code == 200

    def test_response_has_cpu_data(self, client, auth_headers):
        """验证响应包含 CPU 数据。"""
        response = client.get("/api/v2/machine/current", headers=auth_headers)
        data = response.json()
        assert "cpu_percent" in data
        assert isinstance(data["cpu_percent"], (int, float))

    def test_response_has_memory_data(self, client, auth_headers):
        """验证响应包含内存数据。"""
        response = client.get("/api/v2/machine/current", headers=auth_headers)
        data = response.json()
        assert "mem_percent" in data
        assert "mem_used_mb" in data
        assert "mem_total_mb" in data

    def test_response_has_all_metrics(self, client, auth_headers):
        """验证响应包含所有系统指标。"""
        response = client.get("/api/v2/machine/current", headers=auth_headers)
        data = response.json()
        required_fields = [
            "cpu_percent",
            "mem_percent",
            "mem_used_mb",
            "mem_total_mb",
            "swap_percent",
            "disk_percent",
            "disk_used_mb",
            "disk_total_mb",
            "proc_mem_mb",
            "proc_mem_percent",
            "proc_cpu_percent",
            "proc_workers",
            "net_sent_mb",
            "net_recv_mb",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


# ── TestHistoryEndpoint ───────────────────────────────────────────────────────


class TestHistoryEndpoint:
    """测试 GET /api/v2/machine/history 端点。"""

    def test_returns_200(self, client, auth_headers):
        """验证端点返回 200 状态码。"""
        response = client.get("/api/v2/machine/history", headers=auth_headers)
        assert response.status_code == 200

    def test_response_structure(self, client, auth_headers):
        """验证响应包含 history 数组。"""
        response = client.get("/api/v2/machine/history", headers=auth_headers)
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)

    def test_accepts_minutes_parameter(self, client, auth_headers):
        """验证端点接受 minutes 参数。"""
        response = client.get("/api/v2/machine/history?minutes=5", headers=auth_headers)
        assert response.status_code == 200

    def test_validates_minutes_range(self, client, auth_headers):
        """验证 minutes 参数范围校验。"""
        # 小于最小值
        response = client.get("/api/v2/machine/history?minutes=0", headers=auth_headers)
        assert response.status_code == 422

        # 超过最大值
        response = client.get("/api/v2/machine/history?minutes=20000", headers=auth_headers)
        assert response.status_code == 422

        # 正常范围
        response = client.get("/api/v2/machine/history?minutes=100", headers=auth_headers)
        assert response.status_code == 200


# ── TestServiceHealthEndpoint ─────────────────────────────────────────────────


class TestServiceHealthEndpoint:
    """测试 GET /api/v2/machine/servicehealth 端点。"""

    def test_returns_200(self, client, auth_headers):
        """验证端点返回 200 状态码。"""
        response = client.get("/api/v2/machine/servicehealth", headers=auth_headers)
        assert response.status_code == 200

    def test_response_structure(self, client, auth_headers):
        """验证响应包含 services 数组。"""
        response = client.get("/api/v2/machine/servicehealth", headers=auth_headers)
        data = response.json()
        assert "services" in data
        assert isinstance(data["services"], list)

    def test_includes_all_services(self, client, auth_headers):
        """验证响应包含所有服务状态。"""
        response = client.get("/api/v2/machine/servicehealth", headers=auth_headers)
        data = response.json()
        service_names = [s["name"] for s in data["services"]]
        assert "machine" in service_names
        assert "core" in service_names
        assert "migrate" in service_names

    def test_each_service_has_health(self, client, auth_headers):
        """验证每个服务都有 health 字段。"""
        response = client.get("/api/v2/machine/servicehealth", headers=auth_headers)
        data = response.json()
        for service in data["services"]:
            assert "name" in service
            assert "health" in service
            assert isinstance(service["health"], dict)


# ── TestResponseModels ────────────────────────────────────────────────────────


class TestResponseModels:
    """测试 Pydantic 响应模型验证。"""

    def test_current_validates_against_model(self, client, auth_headers):
        """验证 /current 响应符合 MachineCurrentResponseModel。"""
        from app.api.machine.router import MachineCurrentResponseModel

        response = client.get("/api/v2/machine/current", headers=auth_headers)
        data = response.json()

        # Pydantic 模型验证
        model = MachineCurrentResponseModel.model_validate(data)
        assert model.cpu_percent == 12.5
        assert model.mem_percent == 68.2

    def test_history_validates_against_model(self, client, auth_headers):
        """验证 /history 响应符合 MachineHistoryResponseModel。"""
        from app.api.machine.router import MachineHistoryResponseModel

        response = client.get("/api/v2/machine/history", headers=auth_headers)
        data = response.json()

        # Pydantic 模型验证
        model = MachineHistoryResponseModel.model_validate(data)
        assert len(model.history) > 0


# ── TestEdgeCases ─────────────────────────────────────────────────────────────


class TestEdgeCases:
    """测试边界情况和错误处理。"""

    def test_invalid_endpoint(self, client, auth_headers):
        """验证不存在的端点返回 404。"""
        response = client.get("/api/v2/machine/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_invalid_query_parameter_type(self, client, auth_headers):
        """验证无效的查询参数类型。"""
        response = client.get("/api/v2/machine/history?minutes=abc", headers=auth_headers)
        assert response.status_code == 422

    def test_missing_api_key(self, client):
        """验证缺少 API Key 返回 422 (header 缺失导致验证失败)。"""
        response = client.get("/api/v2/machine/check")
        assert response.status_code == 422

    def test_invalid_api_key(self, client):
        """验证无效 API Key 返回 401。"""
        response = client.get("/api/v2/machine/check", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
