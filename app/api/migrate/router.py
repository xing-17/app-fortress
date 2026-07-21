from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.bridges.migrate._service.request import MigrateRequest
from app.bridges.migrate._service.service import MigrateService

MigrateRouter = APIRouter(
    prefix="/migrate",
    tags=["migrate"],
)


# ── Dependency Functions ──────────────────────────────────────────────────────


def get_migrate_service(request: Request) -> MigrateService:
    """从 app state 获取 MigrateService。"""
    return request.app.state.api.migrate_service


# ── Response Models ───────────────────────────────────────────────────────────


class MigrateSubmitResponseModel(BaseModel):
    request_id: str


@MigrateRouter.post(
    "/submit",
    response_model=MigrateSubmitResponseModel,
    summary="Submit a new migrate request",
)
def submit(request: Request, body: MigrateRequest) -> MigrateSubmitResponseModel:
    """
    URL: POST /api/v2/migrate/submit

    提交一个新的 migrate request 到执行队列。

    """
    try:
        migrate_service: MigrateService = get_migrate_service(request)
        request_id = migrate_service.submit(body)
        model = MigrateSubmitResponseModel.model_validate({"request_id": request_id})
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MigrateLookupResponseModel(BaseModel):
    status: str
    started_at: str | None
    finished_at: str | None
    duration_seconds: float | None
    request: dict
    node: dict | None
    error: str | None


@MigrateRouter.get(
    "/lookup/{request_id}",
    response_model=MigrateLookupResponseModel,
    summary="Lookup the status of a migrate request",
)
def lookup(
    request: Request,
    request_id: str,
) -> MigrateLookupResponseModel:
    """
    URL: GET /api/v2/migrate/lookup/{request_id}

    根据 request_id 查询 MigrateRequest 的执行状态。
    如果 request_id 不存在，则返回 404 错误。

    """
    try:
        migrate_service: MigrateService = get_migrate_service(request)
        result = migrate_service.lookup(request_id)
        model = MigrateLookupResponseModel.model_validate(result)
        return model
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MigrateCancelResponseModel(BaseModel):
    canceled: str


@MigrateRouter.post(
    "/cancel/{request_id}",
    response_model=MigrateCancelResponseModel,
    summary="Cancel a migrate request",
)
def cancel(request: Request, request_id: str) -> MigrateCancelResponseModel:
    """
    URL: POST /api/v2/migrate/cancel/{request_id}

    取消一个正在执行或排队中的 migrate request。

    """
    try:
        migrate_service: MigrateService = get_migrate_service(request)
        migrate_service.cancel(request_id)
        model = MigrateCancelResponseModel.model_validate({"canceled": request_id})
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MigrateHistoryResponseModel(BaseModel):
    history: list[dict[str, Any]]


@MigrateRouter.get(
    "/history",
    response_model=MigrateHistoryResponseModel,
    summary="Get the history of migrate requests",
)
def history(request: Request) -> MigrateHistoryResponseModel:
    """
    URL: GET /api/v2/migrate/history

    获取所有 migrate requests 的历史记录。

    """
    try:
        migrate_service: MigrateService = get_migrate_service(request)
        history_data = migrate_service.history()
        model = MigrateHistoryResponseModel.model_validate({"history": history_data})
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MigrateResetResponseModel(BaseModel):
    status: str


@MigrateRouter.post(
    "/reset",
    response_model=MigrateResetResponseModel,
    summary="Reset the migrate service",
)
def reset(request: Request) -> MigrateResetResponseModel:
    """
    URL: POST /api/v2/migrate/reset

    重置 migrate service，清空所有队列和历史记录。

    """
    try:
        migrate_service: MigrateService = get_migrate_service(request)
        migrate_service.reset()
        model = MigrateResetResponseModel.model_validate({"status": "ok"})
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
