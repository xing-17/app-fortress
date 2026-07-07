from __future__ import annotations

import tushare

from app.bridges.resources.providers.base.session import BaseSession
from app.common.setting.bridges import TushareProviderSetting


class TushareSession(BaseSession):
    """
    Tushare 会话管理。

    封装 tushare.pro_api 连接的创建与生命周期管理，继承 BaseSession 的
    TTL 自动刷新机制。通过 setting.secret(token) 与 setting.timeout 初始化
    Tushare Pro API 连接。

    Attributes:
        继承自 BaseSession 的所有属性

    Example:
        >>> setting = TushareProviderSetting(
        ...     name="tushare",
        ...     type="tushare",
        ...     secret="your-token",
        ...     timeout=60
        ... )
        >>> session = TushareSession(setting=setting)
        >>> api = session.get_session()
        >>> df = api.daily(ts_code="000001.SZ")

    Notes:
        - token 从 setting.secret 读取
        - timeout 控制 API 请求超时时间
        - 返回的是 tushare.pro_api 实例
    """

    def __init__(
        self,
        setting: TushareProviderSetting,
    ) -> None:
        super().__init__(setting=setting)
        self._set_log_prefix(f"TushareSession({self.name})")

    def _create_session(self) -> tushare.pro_api:
        return tushare.pro_api(
            token=self.setting.secret,
            timeout=self.setting.timeout,
        )
