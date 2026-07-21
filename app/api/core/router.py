from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.bridges.core._service.request import CoreRequest
from app.bridges.core._service.service import CoreService

CoreRouter = APIRouter(
    prefix="/core",
    tags=["core"],
)


# ── Dependency Functions ──────────────────────────────────────────────────────


def get_core_service(request: Request) -> CoreService:
    """从 app state 获取 CoreService。"""
    return request.app.state.api.core_service


# ── Response Models ───────────────────────────────────────────────────────


class CoreSubmitResponseModel(BaseModel):
    request_id: str


@CoreRouter.post(
    "/submit",
    response_model=CoreSubmitResponseModel,
    summary="Submit a new core request",
)
def submit(request: Request, body: CoreRequest) -> CoreSubmitResponseModel:
    """
    URL: POST /api/v2/core/submit

    提交一个新的 core request 到执行队列。

    """
    try:
        core_service: CoreService = get_core_service(request)
        request_id = core_service.submit(body)
        model = CoreSubmitResponseModel.model_validate({"request_id": request_id})
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CoreLookupResponseModel(BaseModel):
    status: str
    error: str | None
    started_at: str | None
    finished_at: str | None
    duration_seconds: float | None
    request: dict[str, Any]
    counts: dict[str, int]
    progress: dict[str, Any]
    pipeline_nodes: list[dict[str, Any]] = []


@CoreRouter.get(
    "/lookup/{request_id}",
    response_model=CoreLookupResponseModel,
    summary="Lookup the status of a core request",
)
def lookup(
    request: Request,
    request_id: str,
) -> CoreLookupResponseModel:
    """
    URL: GET /api/v2/core/lookup/{request_id}

    根据 request_id 查询 CoreRequest 的执行状态。
    如果 request_id 不存在，则返回 404 错误。

    """
    try:
        core_service: CoreService = get_core_service(request)
        result: dict = core_service.lookup(request_id)
        model = CoreLookupResponseModel.model_validate(result)
        return model
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CoreCancelResponseModel(BaseModel):
    canceled: str


@CoreRouter.post(
    "/cancel/{request_id}",
    response_model=CoreCancelResponseModel,
    summary="Cancel a core request",
)
def cancel(request: Request, request_id: str) -> CoreCancelResponseModel:
    """
    URL: POST /api/v2/core/cancel/{request_id}

    取消一个正在执行或排队中的 core request。

    """
    try:
        core_service: CoreService = get_core_service(request)
        core_service.cancel(request_id)
        model = CoreCancelResponseModel.model_validate({"canceled": request_id})
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CoreHistoryResponseModel(BaseModel):
    history: list[dict[str, Any]]


@CoreRouter.get(
    "/history",
    response_model=CoreHistoryResponseModel,
    summary="Get the history of core requests",
)
def history(request: Request) -> CoreHistoryResponseModel:
    """
    URL: GET /api/v2/core/history

    获取所有 core requests 的历史记录。

    """
    try:
        core_service: CoreService = get_core_service(request)
        history_data = core_service.history()
        model = CoreHistoryResponseModel.model_validate({"history": history_data})
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CoreResetResponseModel(BaseModel):
    status: str


@CoreRouter.post(
    "/reset",
    response_model=CoreResetResponseModel,
    summary="Reset the core service",
)
def reset(request: Request) -> CoreResetResponseModel:
    """
    URL: POST /api/v2/core/reset

    重置 core service，清空所有队列和历史记录。

    """
    try:
        core_service: CoreService = get_core_service(request)
        core_service.reset()
        model = CoreResetResponseModel.model_validate({"status": "ok"})
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
