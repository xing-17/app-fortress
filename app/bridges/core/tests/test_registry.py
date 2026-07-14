"""
综合测试：app.bridges.core.registry

覆盖范围
--------
- TestRegistryBasic      基本实例化、加载
- TestRegistryOperations upsert、get、all 操作
- TestRegistryExport     export() 和 describe() 方法
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.bridges.core.registry import BridgesCoreClusterRegistry

# ──────────────────────────────────────────────────────────────────────────────
# TestRegistryBasic
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistryBasic:
    def test_create_registry_with_new_file(self):
        """测试创建新的注册表文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))
            assert registry._path == path
            assert registry._data == {}

    def test_create_registry_loads_existing_file(self):
        """测试加载现有的注册表文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"

            # 先写入一些数据
            existing_data = {
                "req_123": {"status": "DONE"},
                "req_456": {"status": "FAILED"},
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(existing_data, f)

            # 加载注册表
            registry = BridgesCoreClusterRegistry(str(path))
            assert len(registry._data) == 2
            assert "req_123" in registry._data
            assert "req_456" in registry._data

    def test_file_name_property(self):
        """测试 file_name 属性。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "my_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))
            assert registry.file_name == "my_registry.json"


# ──────────────────────────────────────────────────────────────────────────────
# TestRegistryOperations
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistryOperations:
    def test_upsert_new_record(self):
        """测试插入新记录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            data = {"status": "DONE", "rows": 100}
            registry.upsert("req_123", data)

            assert "req_123" in registry._data
            assert registry._data["req_123"] == data

    def test_upsert_updates_existing_record(self):
        """测试更新现有记录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            # 插入初始数据
            registry.upsert("req_123", {"status": "RUNNING"})
            # 更新数据
            registry.upsert("req_123", {"status": "DONE", "rows": 100})

            assert registry._data["req_123"]["status"] == "DONE"
            assert registry._data["req_123"]["rows"] == 100

    def test_upsert_persists_to_file(self):
        """测试 upsert 持久化到文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            data = {"status": "DONE"}
            registry.upsert("req_123", data)

            # 验证文件存在且包含数据
            assert path.exists()
            with open(path, "r") as f:
                file_data = json.load(f)
            assert "req_123" in file_data
            assert file_data["req_123"] == data

    def test_get_returns_existing_record(self):
        """测试 get() 返回现有记录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            data = {"status": "DONE"}
            registry.upsert("req_123", data)

            result = registry.get("req_123")
            assert result == data

    def test_get_returns_none_for_missing_record(self):
        """测试 get() 对不存在的记录返回 None。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            result = registry.get("nonexistent")
            assert result is None

    def test_all_returns_copy_of_data(self):
        """测试 all() 返回数据副本。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            registry.upsert("req_123", {"status": "DONE"})
            registry.upsert("req_456", {"status": "FAILED"})

            all_data = registry.all()
            assert len(all_data) == 2
            assert "req_123" in all_data
            assert "req_456" in all_data

    def test_all_returns_independent_copy(self):
        """测试 all() 返回独立副本（修改不影响原数据）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            registry.upsert("req_123", {"status": "DONE"})
            all_data = registry.all()
            all_data["req_999"] = {"status": "TEST"}

            # 原数据不应该被修改
            assert "req_999" not in registry._data


# ──────────────────────────────────────────────────────────────────────────────
# TestRegistryExport
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistryExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            result = registry.export()
            assert isinstance(result, dict)

    def test_export_contains_path(self):
        """测试导出包含路径。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            result = registry.export()
            assert "path" in result
            assert result["path"] == str(path)

    def test_export_contains_count(self):
        """测试导出包含记录数。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            registry.upsert("req_123", {"status": "DONE"})
            registry.upsert("req_456", {"status": "FAILED"})

            result = registry.export()
            assert result["count"] == 2

    def test_export_contains_data(self):
        """测试导出包含数据。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            registry.upsert("req_123", {"status": "DONE"})

            result = registry.export()
            assert "data" in result
            assert "req_123" in result["data"]

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            result = registry.describe()
            assert isinstance(result, str)
            parsed = json.loads(result)
            assert isinstance(parsed, dict)

    def test_describe_contains_same_data_as_export(self):
        """测试 describe() 包含与 export() 相同的数据。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            registry.upsert("req_123", {"status": "DONE"})

            exported = registry.export()
            described = json.loads(registry.describe())
            assert exported == described


# ──────────────────────────────────────────────────────────────────────────────
# TestRegistryThreadSafety
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistryThreadSafety:
    def test_concurrent_upserts_are_safe(self):
        """测试并发 upsert 操作是安全的。"""
        from concurrent.futures import ThreadPoolExecutor

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesCoreClusterRegistry(str(path))

            def upsert_data(i):
                registry.upsert(f"req_{i}", {"status": "DONE", "index": i})

            # 并发执行 10 次 upsert
            with ThreadPoolExecutor(max_workers=5) as executor:
                list(executor.map(upsert_data, range(10)))

            # 验证所有数据都被正确写入
            assert len(registry._data) == 10
            for i in range(10):
                assert f"req_{i}" in registry._data
                assert registry._data[f"req_{i}"]["index"] == i
