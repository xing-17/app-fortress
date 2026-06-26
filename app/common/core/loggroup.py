from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from xlog import FileGroup

from app.common.core.setting import GlobalSetting


class CoreLogGroupFactory:
    """
    日志文件集群工厂。

    根据全局配置创建 FileGroup 实例，自动解析日志路径、文件大小上限及分组长度。

    Attributes:
        _default_root_dir: 项目根目录（默认）
        _default_log_path: 默认日志目录路径

    Methods:
        new: 根据名称创建并返回 FileGroup 实例
        _resolve_path: 将字符串或 None 解析为 Path 对象

    Example:
        >>> factory = CoreLogGroupFactory()
        >>> group = factory.new("myapp")

    """

    _default_root_dir: ClassVar[Path] = Path(__file__).parent.parent.parent.parent
    _default_log_path: Path = _default_root_dir / "logs"

    @classmethod
    def new(
        cls,
        name: str,
    ) -> FileGroup:
        log_path: Path | None = GlobalSetting.system.log_path
        log_file_max_mb: int = GlobalSetting.system.log_file_max_mb
        log_group_max_len: int = GlobalSetting.system.log_group_max_len
        path = cls._resolve_path(
            path=log_path,
            default=cls._default_log_path,
        )
        return FileGroup(
            path=path,
            name=name,
            max_size_mb=log_file_max_mb,
            max_len=log_group_max_len,
        )

    @staticmethod
    def _resolve_path(
        path: str | Path | None = None,
        default: Path | None = None,
    ) -> Path:
        if path is None:
            return default
        return Path(path).expanduser().resolve()


# ── 全局单例 ──────────────────────────────────────────────────────────────────────────────
# 在模块加载时即创建全局单例，供全局访问和使用
GlobalLogGroupFactory: CoreLogGroupFactory = CoreLogGroupFactory()
GlobalLogGroup: FileGroup = GlobalLogGroupFactory.new("global")
