from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.api.core.router import CoreRouter
from app.api.machine.router import MachineRouter
from app.api.migrate.router import MigrateRouter
from app.bridges.core._service.service import CoreService
from app.bridges.machine._service.service import MachineService
from app.bridges.migrate._service.service import MigrateService
from app.common.setting.api import ApiSetting


class FortressApi:
    def __init__(
        self,
        setting: ApiSetting,
    ) -> None:
        self.setting = setting

        self.machine_service = MachineService()
        self.machine_service.start()

        self.core_service = CoreService()
        self.core_service.start()

        self.migrate_service = MigrateService()
        self.migrate_service.start()

        # FastAPI
        self.app = FastAPI(
            title="Fortress",
            description="Fortress API",
            version=setting.version,
            lifespan=self._lifespan,
        )
        self.app.state.api = self
        self._setup_routes(prefix="/api/v2")

    def _verify_api_key(
        self,
        x_api_key: str = Header(..., alias="X-API-Key"),
    ) -> None:
        if x_api_key != self.setting.key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )

    def _setup_routes(self, prefix: str) -> None:
        auth = [Depends(self._verify_api_key)]
        for router in [
            MachineRouter,
            CoreRouter,
            MigrateRouter,
        ]:
            self.app.include_router(
                router,
                prefix=prefix,
                dependencies=auth,
            )

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        yield  # workers 已在 __init__ 启动

    def run(self) -> None:
        uvicorn.run(
            self.app,
            host=self.setting.host,
            port=self.setting.port,
        )
