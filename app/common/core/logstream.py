from __future__ import annotations

from xlog import (
    ColorText,
    ColorTree,
    FormatLike,
    GroupLike,
    LogStream,
    Text,
    Tree,
)

from app.common.core.loggroup import GlobalLogGroup
from app.common.core.setting import GlobalSetting


class CoreLogStreamFactory:
    """
    日志流工厂。

    根据全局配置创建 LogStream 实例，自动解析日志级别与输出格式。

    Attributes:
        _log_format_mapping: 日志格式名称（字符串）到格式类的映射表

    Methods:
        new: 根据名称和可选分组创建并返回 LogStream 实例
        _resolve_log_format: 根据全局配置解析并实例化对应的日志格式类

    Example:
        >>> factory = CoreLogStreamFactory()
        >>> stream = factory.new("myapp")

    """

    _log_format_mapping: dict[str, type[FormatLike]] = {
        "TEXT": Text,
        "TREE": Tree,
        "COLORTEXT": ColorText,
        "COLORTREE": ColorTree,
    }

    @classmethod
    def new(
        cls,
        name: str,
        groups: list[GroupLike] | None = None,
    ) -> LogStream:
        log_level: str | None = GlobalSetting.system.log_level
        log_format: str | None = cls._resolve_log_format()
        log_groups: list[GroupLike] = groups or [GlobalLogGroup]
        return LogStream(
            name=name,
            level=log_level,
            verbose=True,
            format=log_format,
            groups=log_groups,
        )

    @staticmethod
    def _resolve_log_format() -> FormatLike:
        format = GlobalSetting.system.log_format.upper()
        format_callable = CoreLogStreamFactory._log_format_mapping.get(
            format,
            Text,
        )
        return format_callable()


# ── 全局单例 ──────────────────────────────────────────────────────────────────────────────
# 在模块加载时即创建全局单例，供全局访问和使用
GlobalLogStreamFactory: CoreLogStreamFactory = CoreLogStreamFactory()
GlobalLogStream: LogStream = GlobalLogStreamFactory.new("global")
