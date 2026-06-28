from __future__ import annotations

from app.common.setting.base import BaseSetting


class SystemSetting(BaseSetting):
    """
    系统配置。

    Attributes:
        name: 应用名称
        version: 应用版本
        alias: 应用别名
        env: 运行环境 (默认为 "prod")
        timezone: 时区 (默认为 "UTC")
        log_level: 日志级别 (默认为 "INFO")
        log_format: 日志格式 (默认为 "TEXT")
        log_path: 日志路径 (默认为 None, 即只输出到控制台)
        log_file_max_mb: int = 10
        log_group_max_len: int = 10000

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
    version: str = "1.0.0"
    alias: str = "default"
    env: str = "prod"
    timezone: str = "UTC"
    log_level: str = "INFO"
    log_format: str = "TEXT"
    log_path: str = "./logs"
    log_file_max_mb: int = 10
    log_group_max_len: int = 10000
