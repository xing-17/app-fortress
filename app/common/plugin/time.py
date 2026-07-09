from __future__ import annotations

from datetime import date, datetime, time
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

    def _get_current_date(self) -> date:
        return datetime.now(self._time_zoneinfo).date()

    def _read_date(
        self,
        value: str | date | None = None,
        format: str | None = "%Y-%m-%d",
    ) -> date:
        if value is None or value == "":
            return self._get_current_date()
        if isinstance(value, date):
            return value
        return datetime.strptime(value, format).date()

    def _read_time(
        self,
        value: str | time | None = None,
        format: str | None = "%H:%M:%S",
    ) -> time:
        if value is None or value == "":
            return self._get_current_datetime().time()
        if isinstance(value, time):
            return value
        return datetime.strptime(value, format).time()

    def _read_datetime(
        self,
        value: str | datetime | None = None,
        format: str | None = "%Y-%m-%d %H:%M:%S",
    ) -> datetime:
        if value is None or value == "":
            return self._get_current_datetime()
        if isinstance(value, datetime):
            return value
        return datetime.strptime(value, format)

    def _read_timestamp(
        self,
        value: str | float | int | None = None,
    ) -> float:
        if value is None or value == "":
            return self._get_current_timestamp()
        if isinstance(value, (float, int)):
            return float(value)
        return float(value)
