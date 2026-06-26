from __future__ import annotations

from typing import Any

from app.common.core.logstream import GlobalLogStreamFactory
from app.common.core.setting import GlobalSetting


class LogPlugin:
    """
    日志混入插件。

    为子类提供结构化日志能力，日志流按需延迟初始化，支持自定义名称与输出分组。
    通过混入方式附加到任意类，子类可通过 `_log_name` 和 `_log_groups` 覆盖默认行为。

    Attributes:
        _log_stream: 延迟初始化的 LogStream 实例
        _log_prefix: 可选的日志消息前缀

    Methods:
        log: 输出指定级别的结构化日志
        info: 输出 INFO 级别日志
        debug: 输出 DEBUG 级别日志
        warning: 输出 WARNING 级别日志
        error: 输出 ERROR 级别日志

    Example:
        >>> class MyService(LogPlugin):
        ...     pass
        >>> svc = MyService()
        >>> svc.info("service started")

    """

    def __ensure_log_stream(self) -> None:
        if not hasattr(self, "_log_stream"):
            self._log_stream = GlobalLogStreamFactory.new(
                name=getattr(self, "_log_name", type(self).__name__.lower()),
                groups=getattr(self, "_log_groups", None),
            )

    def _set_log_prefix(
        self,
        prefix: str,
    ) -> None:
        self._log_prefix = prefix or ""

    def _resolve_log_message(
        self,
        msg: str,
    ) -> str:
        if hasattr(self, "_log_prefix"):
            return f"{self._log_prefix} {msg}"
        else:
            return msg

    def log(
        self,
        message: str,
        level: str | int | None = None,
        code: int | None = None,
        context: dict[str, str] | None = None,
        tags: dict[str, str] | None = None,
        metrics: dict[str, str] | None = None,
    ) -> None:
        self.__ensure_log_stream()
        message = self._resolve_log_message(message)
        timezone = GlobalSetting.system.timezone
        self._log_stream.log(
            message=message,
            level=level,
            code=code,
            context=context,
            tags=tags,
            metrics=metrics,
            tz=timezone,
        )

    def info(
        self,
        message: str,
        **kwargs: Any,
    ) -> None:
        self.log(message, level="INFO", **kwargs)

    def debug(
        self,
        message: str,
        **kwargs: Any,
    ) -> None:
        self.log(message, level="DEBUG", **kwargs)

    def warning(
        self,
        message: str,
        **kwargs: Any,
    ) -> None:
        self.log(message, level="WARNING", **kwargs)

    def error(
        self,
        message: str,
        **kwargs: Any,
    ) -> None:
        self.log(message, level="ERROR", **kwargs)
