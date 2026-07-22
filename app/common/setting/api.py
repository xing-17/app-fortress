from __future__ import annotations

from app.common.setting.base import BaseSetting


class ApiSetting(BaseSetting):
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 7963
    key: str = ""
