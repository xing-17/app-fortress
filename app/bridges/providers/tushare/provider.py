from __future__ import annotations

from typing import Any

from app.bridges.providers.base.factory import ProviderFactory
from app.bridges.providers.base.provider import BaseProvider
from app.bridges.providers.tushare.session import TushareSession
from app.common.core.setting import GlobalSetting
from app.common.setting.bridges import (
    BridgesSetting,
    TushareProviderSetting,
)

_TYPE_NAME = "tushare"


@ProviderFactory.register(_TYPE_NAME)
class TushareProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__()
        self._set_log_prefix(f"TushareProvider({self.name})")
        self._session: TushareSession = self._create_session()

    @property
    def setting(self) -> TushareProviderSetting:
        b_setting: BridgesSetting = GlobalSetting.bridges
        return b_setting.get_provider(self._TYPE_NAME)

    def _create_session(self) -> TushareSession:
        return TushareSession(
            name=self.name,
            type=self.type,
            region=self.region,
            ttl_seconds=self.setting.ttl_seconds,
            ttl_margin=self.setting.ttl_margin,
        )

    def call(
        self,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        pass

    def export(self) -> dict[str, Any]:
        return {
            "setting": self.setting.export(),
            "session": self._session.export(),
        }
