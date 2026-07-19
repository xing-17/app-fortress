"""
综合测试：app.bridges.core._service.registry

覆盖范围
--------
- TestCoreRegistryInit      初始化、文件创建
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

from app.bridges.core._service.registry import CoreRegistry

# ──────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────────────────────


def _make_registry(max_items: int = 100) -> tuple[CoreRegistry, str]:
    """创建使用临时目录的 CoreRegistry，返回 (registry, dir_path)。"""
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, "registry.json")
    registry = CoreRegistry(path=path, max_items=max_items)
    return registry, tmp_dir


# ──────────────────────────────────────────────────────────────────────────────
# TestCoreRegistryInit
# ──────────────────────────────────────────────────────────────────────────────


class TestCoreRegistryInit:
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
            json.dump({"req_existing": {"status": "DONE"}}, f)

        # 重新加载
        registry2 = CoreRegistry(path=path)
        assert registry2.get("req_existing") is not None
        assert registry2.get("req_existing")["status"] == "DONE"


# ──────────────────────────────────────────────────────────────────────────────
# TestUpsertAndGet
# ──────────────────────────────────────────────────────────────────────────────


class TestUpsertAndGet:
    def test_upsert_and_get_basic(self):
        """测试 upsert() 和 get() 基本操作。"""
        registry, _ = _make_registry()
        registry.upsert("req_001", {"status": "DONE"})
        result = registry.get("req_001")
        assert result is not None
        assert result["status"] == "DONE"

    def test_get_returns_none_for_missing_key(self):
        """测试 get() 对不存在的 key 返回 None。"""
        registry, _ = _make_registry()
        assert registry.get("nonexistent") is None

    def test_upsert_overwrites_existing(self):
        """测试 upsert() 覆盖已有记录。"""
        registry, _ = _make_registry()
        registry.upsert("req_001", {"status": "RUNNING"})
        registry.upsert("req_001", {"status": "DONE"})
        result = registry.get("req_001")
        assert result["status"] == "DONE"

    def test_upsert_adds_upserted_at_timestamp(self):
        """测试 upsert() 自动添加 __upserted_at__ 时间戳。"""
        registry, _ = _make_registry()
        registry.upsert("req_001", {"status": "DONE"})
        result = registry.get("req_001")
        assert "__upserted_at__" in result

    def test_upsert_persists_to_disk(self):
        """测试 upsert() 立即写入磁盘。"""
        registry, tmp_dir = _make_registry()
        path = os.path.join(tmp_dir, "registry.json")
        registry.upsert("req_001", {"status": "DONE"})

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "req_001" in data

    def test_get_returns_deepcopy(self):
        """测试 get() 返回深拷贝，修改不影响注册表。"""
        registry, _ = _make_registry()
        registry.upsert("req_001", {"status": "DONE", "nested": {"key": "value"}})
        result = registry.get("req_001")
        result["status"] = "MODIFIED"
        result["nested"]["key"] = "changed"
        # 原注册表不受影响
        original = registry.get("req_001")
        assert original["status"] == "DONE"
        assert original["nested"]["key"] == "value"


# ──────────────────────────────────────────────────────────────────────────────
# TestAll
# ──────────────────────────────────────────────────────────────────────────────


class TestAll:
    def test_all_returns_all_items(self):
        """测试 all() 返回所有记录。"""
        registry, _ = _make_registry()
        registry.upsert("req_001", {"status": "DONE"})
        registry.upsert("req_002", {"status": "FAILED"})
        result = registry.all()
        assert len(result) == 2
        assert "req_001" in result
        assert "req_002" in result

    def test_all_returns_empty_dict_initially(self):
        """测试初始时 all() 返回空字典。"""
        registry, _ = _make_registry()
        assert registry.all() == {}

    def test_all_returns_deepcopy(self):
        """测试 all() 返回深拷贝。"""
        registry, _ = _make_registry()
        registry.upsert("req_001", {"status": "DONE"})
        result = registry.all()
        result["req_001"]["status"] = "MODIFIED"
        original = registry.get("req_001")
        assert original["status"] == "DONE"


# ──────────────────────────────────────────────────────────────────────────────
# TestRemove
# ──────────────────────────────────────────────────────────────────────────────


class TestRemove:
    def test_remove_deletes_item(self):
        """测试 remove() 删除指定记录。"""
        registry, _ = _make_registry()
        registry.upsert("req_001", {"status": "DONE"})
        registry.remove("req_001")
        assert registry.get("req_001") is None

    def test_remove_nonexistent_key_is_safe(self):
        """测试删除不存在的 key 不抛出异常。"""
        registry, _ = _make_registry()
        registry.remove("nonexistent")  # should not raise

    def test_remove_persists_to_disk(self):
        """测试 remove() 后文件同步更新。"""
        registry, tmp_dir = _make_registry()
        path = os.path.join(tmp_dir, "registry.json")
        registry.upsert("req_001", {"status": "DONE"})
        registry.remove("req_001")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "req_001" not in data


# ──────────────────────────────────────────────────────────────────────────────
# TestReset
# ──────────────────────────────────────────────────────────────────────────────


class TestReset:
    def test_reset_clears_all_items(self):
        """测试 reset() 清空所有记录。"""
        registry, _ = _make_registry()
        registry.upsert("req_001", {"status": "DONE"})
        registry.upsert("req_002", {"status": "FAILED"})
        registry.reset()
        assert registry.all() == {}

    def test_reset_persists_to_disk(self):
        """测试 reset() 后文件同步更新。"""
        registry, tmp_dir = _make_registry()
        path = os.path.join(tmp_dir, "registry.json")
        registry.upsert("req_001", {"status": "DONE"})
        registry.reset()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == {}


# ──────────────────────────────────────────────────────────────────────────────
# TestMaxItems
# ──────────────────────────────────────────────────────────────────────────────


class TestMaxItems:
    def test_max_items_evicts_oldest(self):
        """测试超过 max_items 时驱逐最旧记录。"""
        registry, _ = _make_registry(max_items=3)
        registry.upsert("req_001", {"status": "DONE"})
        registry.upsert("req_002", {"status": "DONE"})
        registry.upsert("req_003", {"status": "DONE"})
        registry.upsert("req_004", {"status": "DONE"})
        # req_001 should be evicted
        assert registry.get("req_001") is None
        assert registry.get("req_004") is not None

    def test_max_items_keeps_count_within_limit(self):
        """测试注册表记录数不超过 max_items。"""
        max_items = 5
        registry, _ = _make_registry(max_items=max_items)
        for i in range(10):
            registry.upsert(f"req_{i:03d}", {"status": "DONE"})
        assert len(registry.all()) <= max_items


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        registry, _ = _make_registry()
        result = registry.export()
        assert isinstance(result, dict)

    def test_export_contains_path(self):
        """测试 export() 包含 path 字段。"""
        registry, _ = _make_registry()
        result = registry.export()
        assert "path" in result

    def test_export_contains_count(self):
        """测试 export() 包含 count 字段。"""
        registry, _ = _make_registry()
        registry.upsert("req_001", {"status": "DONE"})
        result = registry.export()
        assert result["count"] == 1

    def test_export_contains_max(self):
        """测试 export() 包含 max 字段。"""
        registry, _ = _make_registry(max_items=50)
        result = registry.export()
        assert result["max"] == 50

    def test_describe_returns_valid_json(self):
        """测试 describe() 返回有效 JSON 字符串。"""
        registry, _ = _make_registry()
        result = registry.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert "path" in parsed
        assert "count" in parsed
