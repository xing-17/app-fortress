import uvicorn
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager

from app.common.setting.portal import PortalSetting


class FortPortalApi:
    def __init__(
        self,
        setting: PortalSetting,
    ) -> None:
        self.setting = setting

        self.app = FastAPI(
            title="Fort Portal",
            description="Fort Portal API",
            version=setting.version,
        )
        self.app.state.portal = self

    def run(self) -> None:
        uvicorn.run(
            self.app,
            host=self.setting.host,
            port=self.setting.port,
        )

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        yield
