"""
综合测试：app.bridges.base.registry

覆盖范围
--------
- TestInit            初始化和基本属性验证
- TestLoad            load() 处理不存在、有效、损坏的 JSON 文件
- TestUpsert          upsert() 插入/更新记录、自动时间戳、持久化
- TestGet             get() 获取记录并返回 deepcopy
- TestAll             all() 返回所有记录的 deepcopy
- TestRemove          remove() 删除记录并持久化
- TestReset           reset() 清空注册表并持久化
- TestSave            save() 手动刷盘
- TestMaxItems        max_items 自动清理最旧记录
- TestExport          export() 包含必要键且值正确
- TestDescribe        describe() 返回 JSON 格式的描述字符串
- TestThreadSafety    多线程并发访问的安全性
- TestDeepCopy        验证 deepcopy 防止外部修改
- TestOrderPreserved  验证 OrderedDict 保持插入顺序
"""

from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict
from pathlib import Path

from app.bridges.base.registry import BaseRegistry

# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    """测试初始化和基本属性"""

    def test_init_creates_instance_with_name(self):
        reg = BaseRegistry("test", "/tmp/test.json")
        assert reg.name == "test"

    def test_init_stores_path_as_pathlib_path(self):
        reg = BaseRegistry("test", "/tmp/test.json")
        assert isinstance(reg._path, Path)
        assert str(reg._path) == "/tmp/test.json"

    def test_init_creates_lock(self):
        reg = BaseRegistry("test", "/tmp/test.json")
        assert isinstance(reg._lock, type(threading.Lock()))

    def test_init_items_is_empty_ordered_dict(self):
        reg = BaseRegistry("test", "/tmp/test.json")
        assert isinstance(reg._items, OrderedDict)
        assert len(reg._items) == 0

    def test_file_name_is_private_attribute(self):
        reg = BaseRegistry("test", "/tmp/registry/test.json")
        assert reg._file_name == "test.json"

    def test_max_items_default_is_1000(self):
        reg = BaseRegistry("test", "/tmp/test.json")
        assert reg._max_items == 1000

    def test_max_items_custom_value(self):
        reg = BaseRegistry("test", "/tmp/test.json", max_items=500)
        assert reg._max_items == 500


# ──────────────────────────────────────────────────────────────────────────────
# TestLoad
# ──────────────────────────────────────────────────────────────────────────────


class TestLoad:
    """测试 load() 方法处理各种场景"""

    def test_load_when_file_not_exists_creates_empty_registry(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        assert len(reg._items) == 0
        assert path.exists()  # 应该创建文件

    def test_load_when_file_exists_restores_data(self, tmp_path):
        path = tmp_path / "existing.json"
        test_data = {"req_001": {"status": "DONE"}, "req_002": {"status": "PENDING"}}
        path.write_text(json.dumps(test_data))

        reg = BaseRegistry("test", str(path))
        reg.load()

        assert len(reg._items) == 2
        assert reg._items["req_001"]["status"] == "DONE"
        assert reg._items["req_002"]["status"] == "PENDING"

    def test_load_when_file_corrupted_creates_empty_registry(self, tmp_path):
        path = tmp_path / "corrupted.json"
        path.write_text("not valid json {[")

        reg = BaseRegistry("test", str(path))
        reg.load()

        assert len(reg._items) == 0
        assert path.exists()  # 应该重新创建文件

    def test_load_preserves_insertion_order(self, tmp_path):
        path = tmp_path / "ordered.json"
        # 注意：标准 dict 在 Python 3.7+ 也保持插入顺序
        test_data = {"req_003": {}, "req_001": {}, "req_002": {}}
        path.write_text(json.dumps(test_data))

        reg = BaseRegistry("test", str(path))
        reg.load()

        keys = list(reg._items.keys())
        assert keys == ["req_003", "req_001", "req_002"]


# ──────────────────────────────────────────────────────────────────────────────
# TestUpsert
# ──────────────────────────────────────────────────────────────────────────────


class TestUpsert:
    """测试 upsert() 方法的插入、更新和持久化"""

    def test_upsert_inserts_new_record(self, tmp_path):
        path = tmp_path / "upsert.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_001", {"status": "DONE"})

        assert "req_001" in reg._items
        assert reg._items["req_001"]["status"] == "DONE"

    def test_upsert_adds_timestamp(self, tmp_path):
        path = tmp_path / "upsert.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_001", {"status": "DONE"})

        assert "__upserted_at__" in reg._items["req_001"]
        # 验证时间戳格式（ISO 8601）
        timestamp = reg._items["req_001"]["__upserted_at__"]
        assert "T" in timestamp  # ISO 格式包含 T

    def test_upsert_updates_existing_record(self, tmp_path):
        path = tmp_path / "upsert.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_001", {"status": "PENDING"})
        first_timestamp = reg._items["req_001"]["__upserted_at__"]

        time.sleep(0.01)  # 确保时间戳不同
        reg.upsert("req_001", {"status": "DONE"})
        second_timestamp = reg._items["req_001"]["__upserted_at__"]

        assert reg._items["req_001"]["status"] == "DONE"
        assert second_timestamp != first_timestamp

    def test_upsert_persists_to_file_immediately(self, tmp_path):
        path = tmp_path / "upsert.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_001", {"status": "DONE"})

        # 验证文件已写入
        assert path.exists()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "req_001" in data
        assert data["req_001"]["status"] == "DONE"

    def test_upsert_creates_parent_directories(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "dirs" / "registry.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_001", {"status": "DONE"})

        assert path.exists()
        assert path.parent.exists()

    def test_upsert_does_not_mutate_input_data(self, tmp_path):
        path = tmp_path / "upsert.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        original_data = {"status": "DONE", "nested": {"value": 42}}
        reg.upsert("req_001", original_data)

        # 修改注册表中的数据
        reg._items["req_001"]["status"] = "CHANGED"
        reg._items["req_001"]["nested"]["value"] = 999

        # 原始数据不应该改变
        assert original_data["status"] == "DONE"
        assert original_data["nested"]["value"] == 42

    def test_upsert_moves_existing_key_to_end(self, tmp_path):
        """OrderedDict 特性：更新已有 key 会移到末尾"""
        path = tmp_path / "upsert.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_001", {"order": 1})
        reg.upsert("req_002", {"order": 2})
        reg.upsert("req_003", {"order": 3})
        reg.upsert("req_001", {"order": 1, "updated": True})  # 更新第一个

        keys = list(reg._items.keys())
        assert keys == ["req_002", "req_003", "req_001"]  # req_001 移到末尾


# ──────────────────────────────────────────────────────────────────────────────
# TestGet
# ──────────────────────────────────────────────────────────────────────────────


class TestGet:
    """测试 get() 方法返回记录和 deepcopy"""

    def test_get_returns_existing_record(self, tmp_path):
        path = tmp_path / "get.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        result = reg.get("req_001")

        assert result is not None
        assert result["status"] == "DONE"
        assert "__upserted_at__" in result

    def test_get_returns_none_for_nonexistent_record(self, tmp_path):
        path = tmp_path / "get.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        result = reg.get("nonexistent")

        assert result is None

    def test_get_returns_deep_copy(self, tmp_path):
        path = tmp_path / "get.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE", "nested": {"value": 42}})

        result = reg.get("req_001")

        # 修改返回的数据
        result["status"] = "CHANGED"
        result["nested"]["value"] = 999

        # 注册表中的数据不应该改变
        assert reg._items["req_001"]["status"] == "DONE"
        assert reg._items["req_001"]["nested"]["value"] == 42


# ──────────────────────────────────────────────────────────────────────────────
# TestAll
# ──────────────────────────────────────────────────────────────────────────────


class TestAll:
    """测试 all() 方法返回所有记录的 deepcopy"""

    def test_all_returns_empty_dict_when_no_data(self, tmp_path):
        path = tmp_path / "all.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        result = reg.all()

        assert result == {}
        assert isinstance(result, dict)

    def test_all_returns_all_records(self, tmp_path):
        path = tmp_path / "all.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})
        reg.upsert("req_002", {"status": "PENDING"})

        result = reg.all()

        assert len(result) == 2
        assert result["req_001"]["status"] == "DONE"
        assert result["req_002"]["status"] == "PENDING"

    def test_all_returns_deep_copy(self, tmp_path):
        path = tmp_path / "all.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE", "nested": {"value": 42}})

        result = reg.all()

        # 修改返回的数据
        result["req_001"]["status"] = "CHANGED"
        result["req_001"]["nested"]["value"] = 999

        # 注册表中的数据不应该改变
        assert reg._items["req_001"]["status"] == "DONE"
        assert reg._items["req_001"]["nested"]["value"] == 42


# ──────────────────────────────────────────────────────────────────────────────
# TestRemove
# ──────────────────────────────────────────────────────────────────────────────


class TestRemove:
    """测试 remove() 方法删除记录"""

    def test_remove_deletes_existing_record(self, tmp_path):
        path = tmp_path / "remove.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})
        reg.upsert("req_002", {"status": "PENDING"})

        reg.remove("req_001")

        assert "req_001" not in reg._items
        assert "req_002" in reg._items
        assert len(reg._items) == 1

    def test_remove_persists_to_file(self, tmp_path):
        path = tmp_path / "remove.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})
        reg.upsert("req_002", {"status": "PENDING"})

        reg.remove("req_001")

        # 验证文件已更新
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "req_001" not in data
        assert "req_002" in data

    def test_remove_nonexistent_record_does_not_raise(self, tmp_path):
        """删除不存在的记录不应该抛出异常"""
        path = tmp_path / "remove.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        # 不应该抛出异常
        reg.remove("nonexistent")


# ──────────────────────────────────────────────────────────────────────────────
# TestReset
# ──────────────────────────────────────────────────────────────────────────────


class TestReset:
    """测试 reset() 方法清空注册表"""

    def test_reset_clears_all_data(self, tmp_path):
        path = tmp_path / "reset.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})
        reg.upsert("req_002", {"status": "PENDING"})

        reg.reset()

        assert len(reg._items) == 0

    def test_reset_persists_empty_state_to_file(self, tmp_path):
        path = tmp_path / "reset.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        reg.reset()

        # 验证文件已清空
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == {}


# ──────────────────────────────────────────────────────────────────────────────
# TestSave
# ──────────────────────────────────────────────────────────────────────────────


class TestSave:
    """测试 save() 方法手动刷盘"""

    def test_save_writes_to_disk(self, tmp_path):
        path = tmp_path / "save.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        # 直接修改内部数据（不通过 upsert，模拟特殊场景）
        reg._items["req_001"] = {"status": "DONE", "__upserted_at__": "2026-01-01T00:00:00"}

        reg.save()

        # 验证文件已写入
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "req_001" in data


# ──────────────────────────────────────────────────────────────────────────────
# TestMaxItems
# ──────────────────────────────────────────────────────────────────────────────


class TestMaxItems:
    """测试 max_items 自动清理最旧的记录"""

    def test_max_items_removes_oldest_entries(self, tmp_path):
        path = tmp_path / "maxitems.json"
        reg = BaseRegistry("test", str(path), max_items=3)
        reg.load()

        reg.upsert("req_001", {"order": 1})
        reg.upsert("req_002", {"order": 2})
        reg.upsert("req_003", {"order": 3})
        reg.upsert("req_004", {"order": 4})  # 应该删除 req_001

        assert len(reg._items) == 3
        assert "req_001" not in reg._items
        assert "req_002" in reg._items
        assert "req_003" in reg._items
        assert "req_004" in reg._items

    def test_max_items_persists_cleanup_to_file(self, tmp_path):
        path = tmp_path / "maxitems.json"
        reg = BaseRegistry("test", str(path), max_items=2)
        reg.load()

        reg.upsert("req_001", {"order": 1})
        reg.upsert("req_002", {"order": 2})
        reg.upsert("req_003", {"order": 3})

        # 验证文件只包含最新的 2 条记录
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 2
        assert "req_001" not in data

    def test_max_items_cleanup_on_save(self, tmp_path):
        """save() 时会触发 max_items 清理"""
        path = tmp_path / "maxitems.json"

        # 先创建包含 5 条记录的文件
        test_data = {f"req_{i:03d}": {"order": i} for i in range(1, 6)}
        path.write_text(json.dumps(test_data))

        # 用 max_items=3 加载
        reg = BaseRegistry("test", str(path), max_items=3)
        reg.load()

        # load() 不会自动清理，需要手动 save() 或 upsert() 触发 _flush()
        assert len(reg._items) == 5  # 加载了所有 5 条

        # 手动 save() 触发清理
        reg.save()
        assert len(reg._items) == 3  # 清理后只剩 3 条


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    """测试 export() 方法返回注册表元数据"""

    def test_export_contains_required_keys(self, tmp_path):
        path = tmp_path / "export.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        result = reg.export()

        assert "path" in result
        assert "file" in result
        assert "count" in result
        assert "max" in result
        assert "items" in result

    def test_export_values_are_correct(self, tmp_path):
        path = tmp_path / "export.json"
        reg = BaseRegistry("test", str(path), max_items=500)
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})
        reg.upsert("req_002", {"status": "PENDING"})

        result = reg.export()

        assert result["path"] == str(path)
        assert result["file"] == "export.json"
        assert result["count"] == 2
        assert result["max"] == 500
        assert len(result["items"]) == 2

    def test_export_items_not_deepcopied(self, tmp_path):
        """export() 中的 _export_items() 不使用 deepcopy（性能优化）"""
        path = tmp_path / "export.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        result = reg.export()

        # _export_items() 返回的是普通 dict(self._items)，没有 deepcopy
        # 所以这里不验证隔离性，只验证数据正确
        assert result["items"]["req_001"]["status"] == "DONE"


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    """测试 describe() 方法返回 JSON 字符串"""

    def test_describe_returns_json_string(self, tmp_path):
        path = tmp_path / "describe.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        result = reg.describe()

        assert isinstance(result, str)

    def test_describe_is_valid_json(self, tmp_path):
        path = tmp_path / "describe.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        result = reg.describe()

        # 应该可以解析为 JSON
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_describe_contains_export_data(self, tmp_path):
        path = tmp_path / "describe.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        result = reg.describe()
        data = json.loads(result)

        assert data["count"] == 1
        assert "req_001" in data["items"]


# ──────────────────────────────────────────────────────────────────────────────
# TestThreadSafety
# ──────────────────────────────────────────────────────────────────────────────


class TestThreadSafety:
    """测试多线程并发访问的安全性"""

    def test_concurrent_upserts(self, tmp_path):
        path = tmp_path / "concurrent.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        def upsert_worker(index):
            for i in range(10):
                reg.upsert(f"thread_{index}_item_{i}", {"thread": index, "item": i})

        threads = [threading.Thread(target=upsert_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该有 50 条记录（5个线程 x 10条记录）
        assert len(reg._items) == 50

        # 验证文件也正确写入了所有数据
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 50

    def test_concurrent_read_write(self, tmp_path):
        path = tmp_path / "concurrent_rw.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        # 预先插入一些数据
        for i in range(10):
            reg.upsert(f"item_{i}", {"value": i})

        errors = []

        def writer():
            try:
                for i in range(10, 20):
                    reg.upsert(f"item_{i}", {"value": i})
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(20):
                    reg.all()
                    reg.get("item_5")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 不应该有任何异常
        assert len(errors) == 0


# ──────────────────────────────────────────────────────────────────────────────
# TestDeepCopy
# ──────────────────────────────────────────────────────────────────────────────


class TestDeepCopy:
    """专门测试 deepcopy 机制防止外部修改内部状态"""

    def test_upsert_input_isolation(self, tmp_path):
        path = tmp_path / "deepcopy.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        input_data = {"status": "DONE", "config": {"timeout": 30}}
        reg.upsert("req_001", input_data)

        # 修改输入数据
        input_data["status"] = "MODIFIED"
        input_data["config"]["timeout"] = 999

        # 注册表中的数据不应该改变
        assert reg._items["req_001"]["status"] == "DONE"
        assert reg._items["req_001"]["config"]["timeout"] == 30

    def test_get_output_isolation(self, tmp_path):
        path = tmp_path / "deepcopy.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE", "config": {"timeout": 30}})

        output1 = reg.get("req_001")
        output2 = reg.get("req_001")

        # 两次调用返回的是不同的对象
        assert output1 is not output2

        # 修改一个不影响另一个
        output1["status"] = "MODIFIED"
        assert output2["status"] == "DONE"

    def test_all_output_isolation(self, tmp_path):
        path = tmp_path / "deepcopy.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE", "nested": {"value": 42}})

        output = reg.all()

        # 修改返回的嵌套数据
        output["req_001"]["nested"]["value"] = 999

        # 注册表中的数据不应该改变
        assert reg._items["req_001"]["nested"]["value"] == 42


# ──────────────────────────────────────────────────────────────────────────────
# TestOrderPreserved
# ──────────────────────────────────────────────────────────────────────────────


class TestOrderPreserved:
    """测试 OrderedDict 保持插入顺序"""

    def test_insertion_order_preserved(self, tmp_path):
        path = tmp_path / "order.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_003", {"order": 3})
        reg.upsert("req_001", {"order": 1})
        reg.upsert("req_002", {"order": 2})

        keys = list(reg._items.keys())
        assert keys == ["req_003", "req_001", "req_002"]

    def test_order_persisted_to_file(self, tmp_path):
        path = tmp_path / "order.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_003", {"order": 3})
        reg.upsert("req_001", {"order": 1})
        reg.upsert("req_002", {"order": 2})

        # 直接读取文件验证顺序（JSON 格式保持顺序）
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # 检查 req_003 出现在 req_001 之前
            assert content.index("req_003") < content.index("req_001")
            assert content.index("req_001") < content.index("req_002")

        # 重新加载验证顺序
        reg2 = BaseRegistry("test2", str(path))
        reg2.load()

        keys = list(reg2._items.keys())
        assert keys == ["req_003", "req_001", "req_002"]
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        result = reg.describe()
        parsed = json.loads(result)
        assert "path" in parsed
        assert "count" in parsed
        assert "items" in parsed

    def test_describe_matches_export(self, tmp_path):
        path = tmp_path / "describe.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        export_data = reg.export()
        describe_data = json.loads(reg.describe())
        assert export_data == describe_data
