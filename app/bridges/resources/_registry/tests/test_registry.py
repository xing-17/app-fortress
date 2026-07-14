"""
综合测试：app.bridges.resources._registry.registry

覆盖范围
--------
- TestInit            初始化和基本属性验证
- TestLoad            load() 处理不存在、有效、损坏的 JSON 文件
- TestUpsert          upsert() 插入/更新记录并持久化
- TestGet             get() 获取存在和不存在的记录
- TestAll             all() 返回所有记录的副本
- TestClean           clean() 清空注册表并持久化
- TestExport          export() 包含必要键且值正确
- TestDescribe        describe() 返回 JSON 格式的描述字符串
- TestThreadSafety    多线程并发访问的安全性
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from app.bridges.resources._registry.registry import BaseRegistry

# ──────────────────────────────────────────────────────────────────────────────
# TestInit
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
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

    def test_init_data_is_empty_dict(self):
        reg = BaseRegistry("test", "/tmp/test.json")
        assert reg._data == {}

    def test_file_name_matches_path_name(self):
        reg = BaseRegistry("test", "/tmp/registry/test.json")
        assert reg.file_name == "test.json"


# ──────────────────────────────────────────────────────────────────────────────
# TestLoad
# ──────────────────────────────────────────────────────────────────────────────


class TestLoad:
    def test_load_when_file_not_exists_creates_empty_data(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        assert reg._data == {}

    def test_load_when_file_exists_restores_data(self, tmp_path):
        path = tmp_path / "existing.json"
        test_data = {"req_001": {"status": "DONE"}, "req_002": {"status": "PENDING"}}
        path.write_text(json.dumps(test_data))

        reg = BaseRegistry("test", str(path))
        reg.load()
        assert reg._data == test_data

    def test_load_when_file_corrupted_creates_empty_data(self, tmp_path):
        path = tmp_path / "corrupted.json"
        path.write_text("not valid json {[")

        reg = BaseRegistry("test", str(path))
        reg.load()
        assert reg._data == {}

    def test_load_restores_correct_count(self, tmp_path):
        path = tmp_path / "multi.json"
        test_data = {f"req_{i:03d}": {"status": "DONE"} for i in range(5)}
        path.write_text(json.dumps(test_data))

        reg = BaseRegistry("test", str(path))
        reg.load()
        assert len(reg._data) == 5


# ──────────────────────────────────────────────────────────────────────────────
# TestUpsert
# ──────────────────────────────────────────────────────────────────────────────


class TestUpsert:
    def test_upsert_inserts_new_record(self, tmp_path):
        path = tmp_path / "upsert.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_001", {"status": "DONE"})
        assert "req_001" in reg._data
        assert reg._data["req_001"] == {"status": "DONE"}

    def test_upsert_updates_existing_record(self, tmp_path):
        path = tmp_path / "upsert.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_001", {"status": "PENDING"})
        reg.upsert("req_001", {"status": "DONE"})
        assert reg._data["req_001"] == {"status": "DONE"}

    def test_upsert_persists_to_file(self, tmp_path):
        path = tmp_path / "upsert.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_001", {"status": "DONE"})

        # 验证文件已写入
        assert path.exists()
        with open(path, "r") as f:
            data = json.load(f)
        assert data["req_001"] == {"status": "DONE"}

    def test_upsert_creates_parent_directories(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "registry.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        reg.upsert("req_001", {"status": "DONE"})
        assert path.exists()


# ──────────────────────────────────────────────────────────────────────────────
# TestGet
# ──────────────────────────────────────────────────────────────────────────────


class TestGet:
    def test_get_returns_existing_record(self, tmp_path):
        path = tmp_path / "get.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        result = reg.get("req_001")
        assert result == {"status": "DONE"}

    def test_get_returns_none_for_nonexistent_record(self, tmp_path):
        path = tmp_path / "get.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        result = reg.get("nonexistent")
        assert result is None

    def test_get_returns_correct_record_among_multiple(self, tmp_path):
        path = tmp_path / "get.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})
        reg.upsert("req_002", {"status": "PENDING"})

        result = reg.get("req_002")
        assert result == {"status": "PENDING"}


# ──────────────────────────────────────────────────────────────────────────────
# TestAll
# ──────────────────────────────────────────────────────────────────────────────


class TestAll:
    def test_all_returns_empty_dict_when_no_data(self, tmp_path):
        path = tmp_path / "all.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        result = reg.all()
        assert result == {}

    def test_all_returns_all_records(self, tmp_path):
        path = tmp_path / "all.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})
        reg.upsert("req_002", {"status": "PENDING"})

        result = reg.all()
        assert len(result) == 2
        assert result["req_001"] == {"status": "DONE"}
        assert result["req_002"] == {"status": "PENDING"}

    def test_all_returns_shallow_copy(self, tmp_path):
        path = tmp_path / "all.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        result = reg.all()
        # 验证返回的是新字典
        assert result is not reg._data
        # 但内部值是共享的（浅拷贝）
        assert result["req_001"] is reg._data["req_001"]


# ──────────────────────────────────────────────────────────────────────────────
# TestClean
# ──────────────────────────────────────────────────────────────────────────────


class TestClean:
    def test_clean_clears_all_data(self, tmp_path):
        path = tmp_path / "clean.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})
        reg.upsert("req_002", {"status": "PENDING"})

        reg.clean()
        assert reg._data == {}

    def test_clean_persists_empty_state_to_file(self, tmp_path):
        path = tmp_path / "clean.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        reg.clean()

        with open(path, "r") as f:
            data = json.load(f)
        assert data == {}


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_contains_required_keys(self, tmp_path):
        path = tmp_path / "export.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        result = reg.export()
        assert "path" in result
        assert "count" in result
        assert "data" in result

    def test_export_path_matches_registry_path(self, tmp_path):
        path = tmp_path / "export.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        result = reg.export()
        assert result["path"] == str(path)

    def test_export_count_matches_data_length(self, tmp_path):
        path = tmp_path / "export.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})
        reg.upsert("req_002", {"status": "PENDING"})

        result = reg.export()
        assert result["count"] == 2

    def test_export_data_matches_registry_data(self, tmp_path):
        path = tmp_path / "export.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        result = reg.export()
        assert result["data"]["req_001"] == {"status": "DONE"}


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
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
        reg.upsert("req_001", {"status": "DONE"})

        result = reg.describe()
        parsed = json.loads(result)
        assert "path" in parsed
        assert "count" in parsed
        assert "data" in parsed

    def test_describe_matches_export(self, tmp_path):
        path = tmp_path / "describe.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"status": "DONE"})

        export_data = reg.export()
        describe_data = json.loads(reg.describe())
        assert export_data == describe_data


# ──────────────────────────────────────────────────────────────────────────────
# TestThreadSafety
# ──────────────────────────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_upsert_is_safe(self, tmp_path):
        path = tmp_path / "concurrent.json"
        reg = BaseRegistry("test", str(path))
        reg.load()

        def worker(idx):
            reg.upsert(f"req_{idx:03d}", {"status": "DONE", "thread": idx})

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(reg._data) == 10

    def test_concurrent_read_write_is_safe(self, tmp_path):
        path = tmp_path / "concurrent_rw.json"
        reg = BaseRegistry("test", str(path))
        reg.load()
        reg.upsert("req_001", {"counter": 0})

        results = []

        def reader():
            for _ in range(5):
                data = reg.get("req_001")
                if data:
                    results.append(data["counter"])

        def writer(value):
            reg.upsert("req_001", {"counter": value})

        threads = []
        threads.append(threading.Thread(target=reader))
        for i in range(5):
            threads.append(threading.Thread(target=writer, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证没有崩溃，且最终状态一致
        final = reg.get("req_001")
        assert isinstance(final["counter"], int)
        assert 0 <= final["counter"] <= 4
