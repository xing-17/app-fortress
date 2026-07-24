from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.common.setting.portal import PortalSetting
from app.portal._service.instances import InstancesService
from app.portal.router.instances import InstancesRouter

_STATIC_DIR = Path(__file__).resolve().parent.parent / "portal" / "static"


class FortPortalApi:
    """
    Fortress Portal API。

    提供实例管理的 Web 界面和 REST API，包含：
    - GET /              → HTML 控制台首页
    - GET /api/v1/...    → 实例管理接口（需要 API Key 认证）

    Attributes:
        setting: Portal 配置
        instances_service: 实例服务（桥接 Router ↔ Instance）

    """

    def __init__(
        self,
        setting: PortalSetting,
    ) -> None:
        self.setting = setting
        self.instances_service = InstancesService(setting=setting)

        self.app = FastAPI(
            title="Fortress Portal",
            description="Fortress Instance Control Centre",
            version=setting.version,
            lifespan=self._lifespan,
        )
        # 挂载 app 引用，供 router 中的依赖注入使用
        self.app.state.portal = self

        self._setup_static()
        self._setup_routes(prefix="/api/v1")

    # ── Static ────────────────────────────────────────────────────────────────

    def _setup_static(self) -> None:
        """挂载静态资源目录，并注册首页路由。"""
        _STATIC_DIR.mkdir(parents=True, exist_ok=True)
        self.app.mount(
            "/static",
            StaticFiles(directory=str(_STATIC_DIR)),
            name="static",
        )

        @self.app.get("/", response_class=HTMLResponse, include_in_schema=False)
        def index() -> HTMLResponse:
            html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
            # 在服务端注入 API key，避免其出现在任何静态文件中
            key_script = f"<script>window.__FORTRESS_KEY__={json.dumps(self.setting.key)};</script>"
            html = html.replace("</head>", f"{key_script}\n</head>", 1)
            return HTMLResponse(html)

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _verify_api_key(
        self,
        x_api_key: str = Header(default="", alias="X-API-Key"),
    ) -> None:
        if self.setting.key and x_api_key != self.setting.key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )

    # ── Routes ────────────────────────────────────────────────────────────────

    def _setup_routes(self, prefix: str) -> None:
        auth = [Depends(self._verify_api_key)]
        self.app.include_router(
            InstancesRouter,
            prefix=prefix,
            dependencies=auth,
        )

    # ── Lifespan ──────────────────────────────────────────────────────────────

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        yield

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self) -> None:
        uvicorn.run(
            self.app,
            host=self.setting.host,
            port=self.setting.port,
        )
