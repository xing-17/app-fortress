"""
pytest 配置文件。

提供全局 fixtures 和测试会话钩子，处理资源清理和 mock。
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

# ══════════════════════════════════════════════════════════════════════════════
# 关键：创建一个假的 FileGroup 类，不创建真实文件
# ══════════════════════════════════════════════════════════════════════════════


class FakeFileGroup:
    """假的 FileGroup，模拟接口但不创建真实文件。"""

    def __init__(self, path=None, name=None, max_size_mb=None, max_len=None, **kwargs):
        self.path = path
        self.name = name
        self.max_size_mb = max_size_mb
        self.max_len = max_len
        self._closed = False

    def close(self):
        self._closed = True

    def flush(self):
        pass

    def receive(self, *args, **kwargs):
        pass

    def describe(self):
        return f"FakeFileGroup(name={self.name})"

    def export(self):
        return {"name": self.name, "path": str(self.path) if self.path else None}

    def list_events(self):
        return []

    def list_streams(self):
        return []

    @property
    def alive(self):
        return not self._closed


# 在模块顶层就开始 mock，确保在导入 app.common 之前生效
_filegroup_patcher = patch("xlog.FileGroup", FakeFileGroup)
_filegroup_patcher.start()


# 注册清理函数，在 pytest 退出时停止 patch
def _cleanup_patches():
    _filegroup_patcher.stop()


# pytest 会在退出时调用这个
pytest.register_assert_rewrite("app.common")


@pytest.fixture(scope="session", autouse=True)
def cleanup_global_logstream():
    """
    在测试会话结束时关闭全局日志流，避免 ResourceWarning。

    autouse=True 确保自动应用于所有测试。
    """
    yield  # 测试运行

    # 测试会话结束后清理
    try:
        from app.common.core.loggroup import GlobalLogGroup
        from app.common.core.logstream import GlobalLogStream

        # 关闭全局日志组的文件句柄
        if hasattr(GlobalLogGroup, "close"):
            GlobalLogGroup.close()

        # 刷新全局日志流（如果有缓冲）
        if hasattr(GlobalLogStream, "flush"):
            GlobalLogStream.flush()
    except Exception:
        # 静默失败，不影响测试结果
        pass

    # 额外清理：关闭所有 Python logging 的 handlers
    try:
        # 获取根 logger 并关闭所有 handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            try:
                handler.close()
                root_logger.removeHandler(handler)
            except Exception:
                pass

        # 关闭所有已注册的 loggers 的 handlers
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                try:
                    handler.close()
                    logger.removeHandler(handler)
                except Exception:
                    pass
    except Exception:
        pass


@pytest.fixture(scope="function", autouse=True)
def ensure_test_logs_dir():
    """确保测试日志目录存在。"""
    log_dir = Path(__file__).parent / ".logs"
    log_dir.mkdir(exist_ok=True)
    yield

    # 测试后刷新日志（但不删除）
    try:
        for handler in logging.root.handlers:
            if hasattr(handler, "flush"):
                handler.flush()
    except Exception:
        pass
