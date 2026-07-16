"""
综合测试：app.bridges.migrate.registry

覆盖范围
--------
- TestRegistryBasic      基本实例化、加载
- TestRegistryOperations upsert、get、all 操作
- TestRegistryExport     export() 方法
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.bridges.migrate.registry import BridgesMigrateRegistry

# ──────────────────────────────────────────────────────────────────────────────
# TestRegistryBasic
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistryBasic:
    def test_create_registry_with_new_file(self):
        """测试创建新的注册表文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))
            assert registry._path == path
            assert registry._data == {}

    def test_create_registry_loads_existing_file(self):
        """测试加载现有的注册表文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"

            # 先写入一些数据
            existing_data = {
                "mig_123": {"status": "DONE", "rows": 1000},
                "mig_456": {"status": "FAILED", "error": "Connection timeout"},
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(existing_data, f)

            # 加载注册表
            registry = BridgesMigrateRegistry(str(path))
            assert len(registry._data) == 2
            assert "mig_123" in registry._data
            assert "mig_456" in registry._data

    def test_file_name_property(self):
        """测试 file_name 属性。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "migrate_registry.json"
            registry = BridgesMigrateRegistry(str(path))
            assert registry.file_name == "migrate_registry.json"

    def test_registry_name_is_migrate(self):
        """测试注册表名称为 migrate。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))
            assert hasattr(registry, "name")
            assert registry.name == "migrate"


# ──────────────────────────────────────────────────────────────────────────────
# TestRegistryOperations
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistryOperations:
    def test_upsert_new_record(self):
        """测试插入新记录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            data = {"status": "DONE", "rows": 1000}
            registry.upsert("mig_123", data)

            assert "mig_123" in registry._data
            assert registry._data["mig_123"] == data

    def test_upsert_updates_existing_record(self):
        """测试更新现有记录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            # 插入初始数据
            registry.upsert("mig_123", {"status": "RUNNING"})
            # 更新数据
            registry.upsert("mig_123", {"status": "DONE", "rows": 1000})

            assert registry._data["mig_123"]["status"] == "DONE"
            assert registry._data["mig_123"]["rows"] == 1000

    def test_upsert_persists_to_file(self):
        """测试 upsert 持久化到文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            data = {"status": "DONE", "rows": 1000}
            registry.upsert("mig_123", data)

            # 重新加载注册表，验证数据已持久化
            new_registry = BridgesMigrateRegistry(str(path))
            assert "mig_123" in new_registry._data
            assert new_registry._data["mig_123"] == data

    def test_get_existing_record(self):
        """测试获取存在的记录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            data = {"status": "DONE", "rows": 1000}
            registry.upsert("mig_123", data)

            result = registry.get("mig_123")
            assert result == data

    def test_get_non_existing_record_returns_none(self):
        """测试获取不存在的记录返回 None。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            result = registry.get("mig_999")
            assert result is None

    def test_all_returns_all_records(self):
        """测试 all() 返回所有记录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            registry.upsert("mig_123", {"status": "DONE", "rows": 1000})
            registry.upsert("mig_456", {"status": "FAILED"})

            all_data = registry.all()
            assert len(all_data) == 2
            assert "mig_123" in all_data
            assert "mig_456" in all_data

    def test_all_returns_copy(self):
        """测试 all() 返回数据副本而非原始数据。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            registry.upsert("mig_123", {"status": "DONE"})

            all_data = registry.all()
            all_data["mig_999"] = {"status": "NEW"}

            # 修改返回的数据不应影响注册表内部数据
            assert "mig_999" not in registry._data


# ──────────────────────────────────────────────────────────────────────────────
# TestRegistryExport
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistryExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            exported = registry.export()
            assert isinstance(exported, dict)

    def test_export_contains_path(self):
        """测试 export() 包含 path。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            exported = registry.export()
            assert "path" in exported
            assert str(path) in str(exported["path"])

    def test_export_contains_count(self):
        """测试 export() 包含记录数。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            registry.upsert("mig_123", {"status": "DONE"})
            registry.upsert("mig_456", {"status": "FAILED"})

            exported = registry.export()
            assert "count" in exported
            assert exported["count"] == 2

    def test_export_count_is_zero_for_empty_registry(self):
        """测试空注册表的 export() count 为 0。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_registry.json"
            registry = BridgesMigrateRegistry(str(path))

            exported = registry.export()
            assert exported["count"] == 0
