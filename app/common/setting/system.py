from __future__ import annotations

import json

from pydantic import BaseModel


class SystemSetting(BaseModel):
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
        log_file_max_mb: 日志文件最大大小，单位MB (默认为 10)
        log_group_max_len: 日志分组最大长度 (默认为 10000)

    Methods:
        describe: 返回系统配置的字典细节

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

    def export(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "alias": self.alias,
            "env": self.env,
            "timezone": self.timezone,
            "log_level": self.log_level,
            "log_format": self.log_format,
            "log_path": self.log_path,
            "log_file_max_mb": self.log_file_max_mb,
            "log_group_max_len": self.log_group_max_len,
        }

    def describe(self) -> str:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )
