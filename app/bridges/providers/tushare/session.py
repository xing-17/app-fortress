from __future__ import annotations

import tushare

from app.bridges.providers.base.session import BaseSession
from app.common.core.setting import GlobalSetting

_TYPE_NAME = "tushare"


class TushareSession(BaseSession):
    default_ttl_seconds: int | None = 1800
    default_ttl_margin: int | None = 60

    def __init__(self) -> None:
        setting = GlobalSetting.bridges.get_provider(_TYPE_NAME)
        super().__init__(
            name=setting.name,
            type=setting.type,
            region=setting.region,
            ttl_seconds=setting.ttl_seconds,
            ttl_margin=setting.ttl_margin,
        )
        self._set_log_prefix(f"TushareSession({self.name})")

    @property
    def setting(self):
        return GlobalSetting.bridges.get_provider(_TYPE_NAME)

    def _create_session(self) -> tushare.pro_api:
        return tushare.pro_api(
            token=self.setting.secret,
            timeout=self.setting.timeout,
        )
