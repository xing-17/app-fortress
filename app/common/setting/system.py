from __future__ import annotations

from app.common.setting.base import BaseSetting


class SystemSetting(BaseSetting):
    """
    系统配置。

    Attributes:
        name: str 应用名称
        version: str | None = "1.0.0" 应用版本
        alias: str | None = "default" 应用别名
        env: str | None = "prod" 运行环境
        timezone: str | None = "UTC" 时区
        log_level: str | None = "INFO"
        log_format: str | None = "TEXT"
        log_path: str | None = "./logs"
        log_file_max_mb: int | None = 10
        log_group_max_len: int | None = 10000

    Examples:
        >>> config = SystemSetting(
        ...     name="fortress",
        ...     version="6.0.0",
        ...     alias="伽蓝"
        ... )
        >>> print(config.describe())
        >>> ...

    """

    name: str
    version: str | None = "1.0.0"
    alias: str | None = "default"
    env: str | None = "prod"
    timezone: str | None = "UTC"
    log_level: str | None = "INFO"
    log_format: str | None = "TEXT"
    log_path: str | None = "./logs"
    log_file_max_mb: int | None = 10
    log_group_max_len: int | None = 10000
