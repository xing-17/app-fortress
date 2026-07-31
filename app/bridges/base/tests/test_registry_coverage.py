"""
补充测试：覆盖 registry.py 中未测试的边界情况

覆盖范围
--------
- TestFlushErrorHandling    测试 _flush 方法的异常处理（lines 130-135）
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.bridges.base.registry import BaseRegistry

# ──────────────────────────────────────────────────────────────────────────────
# TestFlushErrorHandling
# ──────────────────────────────────────────────────────────────────────────────


class TestFlushErrorHandling:
    """测试 _flush 方法中的异常处理逻辑"""

    def test_flush_cleans_up_temp_file_on_json_dump_error(self, tmp_path):
        """测试 json.dump 失败时临时文件被清理"""
        path = tmp_path / "test.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        # Mock json.dump 让它抛出异常
        with patch("json.dump", side_effect=ValueError("Mock JSON error")):
            with pytest.raises(ValueError):
                reg._flush()

        # 验证临时文件已被清理（不应该有 .tmp 文件残留）
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_flush_handles_os_unlink_failure_gracefully(self, tmp_path):
        """测试临时文件删除失败时不影响异常抛出"""
        path = tmp_path / "test.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        # Mock json.dump 抛出异常，同时 Mock os.unlink 也抛出 OSError
        with patch("json.dump", side_effect=ValueError("Mock JSON error")):
            with patch("os.unlink", side_effect=OSError("Mock unlink error")):
                with pytest.raises(ValueError):  # 应该抛出原始的 ValueError，而非 OSError
                    reg._flush()

    def test_flush_raises_original_exception_after_cleanup_attempt(self, tmp_path):
        """测试清理尝试后原始异常被正确抛出"""
        path = tmp_path / "test.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        # Mock json.dump 让它抛出 IOError
        with patch("json.dump", side_effect=IOError("Mock IO error")):
            with pytest.raises(IOError, match="Mock IO error"):
                reg._flush()

    def test_flush_handles_permission_error_on_temp_file_creation(self, tmp_path):
        """测试临时文件创建失败时的异常处理"""
        path = tmp_path / "test.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("key1", {"status": "test"})

        # Mock tempfile.mkstemp 让它失败
        with patch(
            "tempfile.mkstemp",
            side_effect=PermissionError("No permission"),
        ):
            with pytest.raises(PermissionError):
                reg._flush()

    def test_flush_succeeds_after_previous_failure(self, tmp_path):
        """测试失败后可以恢复并成功刷盘"""
        path = tmp_path / "test.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        # 第一次 Mock json.dump 失败
        with patch("json.dump", side_effect=ValueError("First failure")):
            with pytest.raises(ValueError):
                reg._flush()

        # 清理并添加正常数据
        with reg._lock:
            reg._items.clear()
            reg._items["good_key"] = {"status": "OK"}

        # 第二次应该成功（不再 Mock）
        reg._flush()
        assert path.exists()

        # 验证数据正确
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["good_key"]["status"] == "OK"

    def test_flush_exception_during_os_replace(self, tmp_path):
        """测试 os.replace 失败时的异常处理"""
        path = tmp_path / "test.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("key1", {"status": "test"})

        # Mock os.replace 让它失败
        with patch("os.replace", side_effect=OSError("Replace failed")):
            with pytest.raises(OSError, match="Replace failed"):
                reg._flush()

    def test_flush_with_write_error_during_json_dump(self, tmp_path):
        """测试 json.dump 写入过程中出错时的处理"""
        path = tmp_path / "test.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("key1", {"status": "test"})

        # Mock json.dump 让它抛出写入错误
        with patch("json.dump", side_effect=IOError("Disk full")):
            with pytest.raises(IOError, match="Disk full"):
                reg._flush()

        # 验证临时文件被清理
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0
