from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.bridges.core._service.service import CoreService
from app.bridges.machine._service.service import MachineService
from app.bridges.migrate._service.service import MigrateService
from app.bridges.resources.base.servicehealth import ServiceHealth

MachineRouter = APIRouter(
    prefix="/machine",
    tags=["machine"],
)


# ── Dependency Functions ──────────────────────────────────────────────────────


def get_machine_service(request: Request) -> MachineService:
    """从 app state 获取 MachineService。"""
    return request.app.state.api.machine_service


def get_core_service(request: Request) -> CoreService:
    """从 app state 获取 CoreService。"""
    return request.app.state.api.core_service


def get_migrate_service(request: Request) -> MigrateService:
    """从 app state 获取 MigrateService。"""
    return request.app.state.api.migrate_service


class MachineCheckResponseModel(BaseModel):
    status: str
    name: str
    version: str | None
    env: str | None
    timezone: str | None


@MachineRouter.get(
    "/check",
    response_model=MachineCheckResponseModel,
    summary="Check the health of the machine service",
)
def check(request: Request) -> MachineCheckResponseModel:
    """
    URL: GET /api/v2/machine/check

    检查系统指标采集器的运行状态。

    """
    machine_service: MachineService = get_machine_service(request)
    try:
        result: dict = machine_service.check()
        model = MachineCheckResponseModel.model_validate(result)
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MachineCurrentResponseModel(BaseModel):
    id: str | None
    created_at: str | None
    timestamp: float | None
    cpu_percent: float | None
    mem_percent: float | None
    mem_used_mb: float | None
    mem_total_mb: float | None
    swap_percent: float | None
    disk_percent: float | None
    disk_used_mb: float | None
    disk_total_mb: float | None
    proc_mem_mb: float | None
    proc_mem_percent: float | None
    proc_cpu_percent: float | None
    proc_workers: int | None
    net_sent_mb: float | None
    net_recv_mb: float | None


@MachineRouter.get(
    "/current",
    response_model=MachineCurrentResponseModel,
    summary="Get the current system metrics",
)
def current(request: Request) -> MachineCurrentResponseModel:
    """
    URL: GET /api/v2/machine/current

    获取当前系统指标数据。

    """
    machine_service: MachineService = get_machine_service(request)
    try:
        result: dict = machine_service.current()
        model = MachineCurrentResponseModel.model_validate(result)
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MachineHistoryResponseModel(BaseModel):
    history: list[MachineCurrentResponseModel]


@MachineRouter.get(
    "/history",
    response_model=MachineHistoryResponseModel,
    summary="Get the historical system metrics",
)
def history(
    request: Request,
    minutes: int | None = Query(default=None, ge=1, le=10000),
) -> MachineHistoryResponseModel:
    """
    URL: GET /api/v2/machine/history?minutes={minutes}

    获取历史系统指标数据。

    Query Parameters:
        minutes: int | None = None
            查询最近多少分钟的历史数据，单位为分钟。
            如果不传，则返回所有历史数据。

    """
    machine_service: MachineService = get_machine_service(request)
    try:
        history: list[dict] = machine_service.history(minutes=minutes)
        model = MachineHistoryResponseModel.model_validate({"history": history})
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ServiceEntryModel(BaseModel):
    name: str
    health: dict


class MachineServiceHealthResponseModel(BaseModel):
    services: list[ServiceEntryModel]


@MachineRouter.get(
    "/servicehealth",
    response_model=MachineServiceHealthResponseModel,
    summary="Get the health status of system services",
)
def servicehealth(request: Request) -> MachineServiceHealthResponseModel:
    """
    URL: GET /api/v2/machine/servicehealth

    获取系统指标采集器的运行状态。

    """
    try:
        result = []
        machine_service: MachineService = get_machine_service(request)
        machine_service_health: ServiceHealth = machine_service.health()
        result.append(
            {
                "name": "machine",
                "health": machine_service_health.export(),
            }
        )
        core_service: CoreService = get_core_service(request)
        core_service_health: ServiceHealth = core_service.health()
        result.append(
            {
                "name": "core",
                "health": core_service_health.export(),
            }
        )
        migrate_service: MigrateService = get_migrate_service(request)
        migrate_service_health: ServiceHealth = migrate_service.health()
        result.append(
            {
                "name": "migrate",
                "health": migrate_service_health.export(),
            }
        )
        model = MachineServiceHealthResponseModel.model_validate({"services": result})
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
