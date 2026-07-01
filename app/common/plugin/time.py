from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.common.core.setting import GlobalSetting


class TimePlugin:
    """
    时间工具混入插件。

    为子类提供时区感知的时间获取能力，时区来源于全局配置，无效时区回退至 UTC。

    Methods:
        _get_current_timestamp: 返回当前时区下的 Unix 时间戳字符串
        _get_current_datetime: 返回当前时区下的 datetime 对象
        _get_current_date: 返回当前时区下的 date 对象

    Example:
        >>> class MyTask(TimePlugin):
        ...     pass
        >>> task = MyTask()
        >>> print(task._get_current_datetime())

    """

    @property
    def _time_zoneinfo(self) -> ZoneInfo:
        try:
            timezone = GlobalSetting.system.timezone
            return ZoneInfo(timezone)
        except Exception:
            return ZoneInfo("UTC")

    def _get_current_timestamp(self) -> float:
        return datetime.now(self._time_zoneinfo).timestamp()

    def _get_current_datetime(self) -> datetime:
        return datetime.now(self._time_zoneinfo)

    def _get_current_date(self) -> datetime.date:
        return datetime.now(self._time_zoneinfo).date()
