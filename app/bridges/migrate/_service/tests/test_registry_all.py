"""
综合测试：app.bridges.migrate._service.registry

覆盖范围
--------
- TestMigrateRegistryInit   初始化、文件创建
- TestUpsertAndGet          upsert() / get() 基本操作
- TestAll                   all() 方法
- TestRemove                remove() 方法
- TestReset                 reset() 方法
- TestMaxItems              max_items 限制
- TestExport                export() 和 describe() 方法
"""

from __future__ import annotations

import json
import os
import tempfile

from app.bridges.migrate._service.registry import MigrateRegistry

# ──────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────────────────────


def _make_registry(max_items: int = 100) -> tuple[MigrateRegistry, str]:
    """创建使用临时目录的 MigrateRegistry，返回 (registry, dir_path)。"""
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, "registry.json")
    registry = MigrateRegistry(path=path, max_items=max_items)
    return registry, tmp_dir


# ──────────────────────────────────────────────────────────────────────────────
# TestMigrateRegistryInit
# ──────────────────────────────────────────────────────────────────────────────


class TestMigrateRegistryInit:
    def test_registry_creates_json_file(self):
        """测试初始化时创建 JSON 文件。"""
        registry, tmp_dir = _make_registry()
        path = os.path.join(tmp_dir, "registry.json")
        assert os.path.exists(path)

    def test_registry_file_is_valid_json(self):
        """测试注册表文件为合法 JSON。"""
        registry, tmp_dir = _make_registry()
        path = os.path.join(tmp_dir, "registry.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_registry_is_empty_on_init(self):
        """测试初始化后注册表为空。"""
        registry, _ = _make_registry()
        assert registry.all() == {}

    def test_registry_loads_existing_file(self):
        """测试可以加载已有 JSON 文件中的数据。"""
        registry, tmp_dir = _make_registry()
        path = os.path.join(tmp_dir, "registry.json")

        # 预先写入数据
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"mig_existing": {"status": "DONE"}}, f)

        # 重新加载
        registry2 = MigrateRegistry(path=path)
        assert registry2.get("mig_existing") is not None
        assert registry2.get("mig_existing")["status"] == "DONE"

    def test_registry_name_is_migrate(self):
        """测试注册表名称为 migrate。"""
        registry, _ = _make_registry()
        assert registry.name == "migrate"


# ──────────────────────────────────────────────────────────────────────────────
# TestUpsertAndGet
# ──────────────────────────────────────────────────────────────────────────────


class TestUpsertAndGet:
    def test_upsert_and_get_basic(self):
        """测试 upsert() 和 get() 基本操作。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE"})
        result = registry.get("mig_001")
        assert result is not None
        assert result["status"] == "DONE"

    def test_get_returns_none_for_missing_key(self):
        """测试 get() 对不存在的 key 返回 None。"""
        registry, _ = _make_registry()
        assert registry.get("nonexistent") is None

    def test_upsert_overwrites_existing(self):
        """测试 upsert() 覆盖已有记录。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "RUNNING"})
        registry.upsert("mig_001", {"status": "DONE"})
        result = registry.get("mig_001")
        assert result["status"] == "DONE"

    def test_upsert_adds_upserted_at_timestamp(self):
        """测试 upsert() 自动添加 __upserted_at__ 时间戳。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE"})
        result = registry.get("mig_001")
        assert "__upserted_at__" in result

    def test_upsert_persists_to_disk(self):
        """测试 upsert() 立即写入磁盘。"""
        registry, tmp_dir = _make_registry()
        path = os.path.join(tmp_dir, "registry.json")
        registry.upsert("mig_001", {"status": "DONE"})

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "mig_001" in data

    def test_get_returns_deepcopy(self):
        """测试 get() 返回深拷贝，修改不影响注册表。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE", "nested": {"key": "value"}})
        result = registry.get("mig_001")
        result["status"] = "MODIFIED"
        result["nested"]["key"] = "changed"
        # 原注册表不受影响
        original = registry.get("mig_001")
        assert original["status"] == "DONE"
        assert original["nested"]["key"] == "value"

    def test_upsert_accepts_dict_data(self):
        """测试 upsert() 接受字典数据。"""
        registry, _ = _make_registry()
        data = {"status": "DONE", "rows": 1000, "error": None}
        registry.upsert("mig_001", data)
        result = registry.get("mig_001")
        assert result["status"] == "DONE"
        assert result["rows"] == 1000


# ──────────────────────────────────────────────────────────────────────────────
# TestAll
# ──────────────────────────────────────────────────────────────────────────────


class TestAll:
    def test_all_returns_all_items(self):
        """测试 all() 返回所有记录。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE"})
        registry.upsert("mig_002", {"status": "FAILED"})
        result = registry.all()
        assert len(result) == 2
        assert "mig_001" in result
        assert "mig_002" in result

    def test_all_returns_empty_dict_initially(self):
        """测试初始时 all() 返回空字典。"""
        registry, _ = _make_registry()
        assert registry.all() == {}

    def test_all_returns_deepcopy(self):
        """测试 all() 返回深拷贝，修改不影响注册表。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE"})
        result = registry.all()
        result["mig_001"]["status"] = "MODIFIED"
        # 原注册表不受影响
        original = registry.get("mig_001")
        assert original["status"] == "DONE"

    def test_all_contains_correct_data(self):
        """测试 all() 返回的数据正确。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE", "rows": 100})
        registry.upsert("mig_002", {"status": "FAILED", "error": "test"})
        result = registry.all()
        assert result["mig_001"]["status"] == "DONE"
        assert result["mig_001"]["rows"] == 100
        assert result["mig_002"]["status"] == "FAILED"
        assert result["mig_002"]["error"] == "test"


# ──────────────────────────────────────────────────────────────────────────────
# TestRemove
# ──────────────────────────────────────────────────────────────────────────────


class TestRemove:
    def test_remove_deletes_item(self):
        """测试 remove() 删除记录。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE"})
        registry.remove("mig_001")
        assert registry.get("mig_001") is None

    def test_remove_nonexistent_key_does_not_raise(self):
        """测试 remove() 不存在的 key 不抛出异常。"""
        registry, _ = _make_registry()
        # Should not raise
        registry.remove("nonexistent")

    def test_remove_persists_to_disk(self):
        """测试 remove() 立即写入磁盘。"""
        registry, tmp_dir = _make_registry()
        path = os.path.join(tmp_dir, "registry.json")
        registry.upsert("mig_001", {"status": "DONE"})
        registry.remove("mig_001")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "mig_001" not in data

    def test_remove_only_affects_specified_key(self):
        """测试 remove() 只删除指定的 key。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE"})
        registry.upsert("mig_002", {"status": "DONE"})
        registry.remove("mig_001")
        assert registry.get("mig_001") is None
        assert registry.get("mig_002") is not None


# ──────────────────────────────────────────────────────────────────────────────
# TestReset
# ──────────────────────────────────────────────────────────────────────────────


class TestReset:
    def test_reset_clears_all_data(self):
        """测试 reset() 清空所有数据。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE"})
        registry.upsert("mig_002", {"status": "DONE"})
        registry.reset()
        assert registry.all() == {}

    def test_reset_persists_to_disk(self):
        """测试 reset() 立即写入磁盘。"""
        registry, tmp_dir = _make_registry()
        path = os.path.join(tmp_dir, "registry.json")
        registry.upsert("mig_001", {"status": "DONE"})
        registry.reset()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == {}

    def test_reset_allows_new_inserts_after(self):
        """测试 reset() 后可以继续插入。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE"})
        registry.reset()
        registry.upsert("mig_002", {"status": "DONE"})
        assert registry.get("mig_002") is not None
        assert registry.get("mig_001") is None


# ──────────────────────────────────────────────────────────────────────────────
# TestMaxItems
# ──────────────────────────────────────────────────────────────────────────────


class TestMaxItems:
    def test_registry_respects_max_items_limit(self):
        """测试注册表遵守 max_items 限制。"""
        registry, _ = _make_registry(max_items=3)
        registry.upsert("mig_001", {"status": "DONE"})
        registry.upsert("mig_002", {"status": "DONE"})
        registry.upsert("mig_003", {"status": "DONE"})
        registry.upsert("mig_004", {"status": "DONE"})  # Should evict oldest
        all_data = registry.all()
        assert len(all_data) == 3
        # 最老的应该被删除
        assert "mig_001" not in all_data

    def test_max_items_evicts_oldest_first(self):
        """测试 max_items 限制优先删除最老的记录。"""
        registry, _ = _make_registry(max_items=2)
        registry.upsert("mig_001", {"status": "DONE"})
        registry.upsert("mig_002", {"status": "DONE"})
        registry.upsert("mig_003", {"status": "DONE"})
        all_data = registry.all()
        assert "mig_001" not in all_data
        assert "mig_002" in all_data
        assert "mig_003" in all_data

    def test_max_items_zero_allows_unlimited(self):
        """测试 max_items 为 0 时无限制。"""
        registry, _ = _make_registry(max_items=0)
        for i in range(10):
            registry.upsert(f"mig_{i:03d}", {"status": "DONE"})
        all_data = registry.all()
        assert len(all_data) == 10


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        registry, _ = _make_registry()
        result = registry.export()
        assert isinstance(result, dict)

    def test_export_contains_file(self):
        """测试 export() 包含 file。"""
        registry, _ = _make_registry()
        result = registry.export()
        assert "file" in result
        assert result["file"] == "registry.json"

    def test_export_contains_path(self):
        """测试 export() 包含 path。"""
        registry, _ = _make_registry()
        result = registry.export()
        assert "path" in result

    def test_export_contains_count(self):
        """测试 export() 包含 count。"""
        registry, _ = _make_registry()
        registry.upsert("mig_001", {"status": "DONE"})
        registry.upsert("mig_002", {"status": "DONE"})
        result = registry.export()
        assert "count" in result
        assert result["count"] == 2

    def test_export_contains_max(self):
        """测试 export() 包含 max。"""
        registry, _ = _make_registry(max_items=100)
        result = registry.export()
        assert "max" in result
        assert result["max"] == 100

    def test_describe_returns_valid_json(self):
        """测试 describe() 返回有效 JSON 字符串。"""
        registry, _ = _make_registry()
        result = registry.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_contains_file(self):
        """测试 describe() 包含 file 数据。"""
        registry, _ = _make_registry()
        result = json.loads(registry.describe())
        assert result["file"] == "registry.json"
