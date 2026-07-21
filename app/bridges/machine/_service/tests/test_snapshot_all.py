"""
综合测试：app.bridges.machine._service.snapshot

覆盖范围
--------
- TestInstantiation    基本实例化和属性验证
- TestFields           字段类型和默认值
- TestExport           export() 方法和时间戳
- TestInheritance      BaseContext 继承特性
"""

from __future__ import annotations

from datetime import datetime

from app.bridges.machine._service.snapshot import MachineSnapshot

# ── TestInstantiation ─────────────────────────────────────────────────────────


class TestInstantiation:
    """测试基本实例化和属性验证。"""

    def test_create_snapshot_with_required_fields(self):
        """使用所有必需字段创建快照。"""
        snapshot = MachineSnapshot(
            cpu_percent=45.2,
            mem_percent=68.5,
            mem_used_mb=8192,
            mem_total_mb=12288,
            swap_percent=10.0,
            disk_percent=75.3,
            disk_used_mb=512000,
            disk_total_mb=680000,
        )
        assert snapshot.cpu_percent == 45.2
        assert snapshot.mem_percent == 68.5
        assert snapshot.mem_used_mb == 8192
        assert snapshot.mem_total_mb == 12288
        assert snapshot.swap_percent == 10.0
        assert snapshot.disk_percent == 75.3
        assert snapshot.disk_used_mb == 512000
        assert snapshot.disk_total_mb == 680000

    def test_create_snapshot_with_all_fields(self):
        """使用所有字段（包括可选字段）创建快照。"""
        snapshot = MachineSnapshot(
            cpu_percent=45.2,
            mem_percent=68.5,
            mem_used_mb=8192,
            mem_total_mb=12288,
            swap_percent=10.0,
            disk_percent=75.3,
            disk_used_mb=512000,
            disk_total_mb=680000,
            proc_mem_mb=256,
            proc_mem_percent=2.08,
            proc_cpu_percent=12.5,
            proc_workers=8,
            net_sent_mb=1024,
            net_recv_mb=2048,
        )
        assert snapshot.proc_mem_mb == 256
        assert snapshot.proc_mem_percent == 2.08
        assert snapshot.proc_cpu_percent == 12.5
        assert snapshot.proc_workers == 8
        assert snapshot.net_sent_mb == 1024
        assert snapshot.net_recv_mb == 2048

    def test_id_prefix_is_correct(self):
        """验证 ID 前缀为 'macs-'。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        assert snapshot.id.startswith("macs-")

    def test_id_length_is_correct(self):
        """验证 ID 总长度（包括前缀）符合预期。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        # ID 格式：macs- + 连字符 + 16位字符 = 22位
        assert len(snapshot.id) == 22

    def test_created_at_is_set_automatically(self):
        """验证 created_at 自动设置为当前时间。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        assert snapshot.created_at is not None
        assert isinstance(snapshot.created_at, datetime)


# ── TestFields ────────────────────────────────────────────────────────────────


class TestFields:
    """测试字段类型和默认值。"""

    def test_required_fields_are_float(self):
        """验证必需字段均为 float 类型。"""
        snapshot = MachineSnapshot(
            cpu_percent=45.2,
            mem_percent=68.5,
            mem_used_mb=8192,
            mem_total_mb=12288,
            swap_percent=10.0,
            disk_percent=75.3,
            disk_used_mb=512000,
            disk_total_mb=680000,
        )
        assert isinstance(snapshot.cpu_percent, float)
        assert isinstance(snapshot.mem_percent, float)
        assert isinstance(snapshot.mem_used_mb, (int, float))
        assert isinstance(snapshot.mem_total_mb, (int, float))
        assert isinstance(snapshot.swap_percent, float)
        assert isinstance(snapshot.disk_percent, float)
        assert isinstance(snapshot.disk_used_mb, (int, float))
        assert isinstance(snapshot.disk_total_mb, (int, float))

    def test_optional_fields_default_to_none(self):
        """验证可选字段默认为 None。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        assert snapshot.proc_mem_mb is None
        assert snapshot.proc_mem_percent is None
        assert snapshot.proc_cpu_percent is None
        assert snapshot.proc_workers is None
        assert snapshot.net_sent_mb is None
        assert snapshot.net_recv_mb is None

    def test_optional_fields_accept_values(self):
        """验证可选字段可以设置值。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
            proc_mem_mb=128.5,
            proc_mem_percent=1.5,
            proc_cpu_percent=5.2,
            proc_workers=4,
            net_sent_mb=512.3,
            net_recv_mb=1024.7,
        )
        assert snapshot.proc_mem_mb == 128.5
        assert snapshot.proc_mem_percent == 1.5
        assert snapshot.proc_cpu_percent == 5.2
        assert snapshot.proc_workers == 4
        assert snapshot.net_sent_mb == 512.3
        assert snapshot.net_recv_mb == 1024.7


# ── TestExport ────────────────────────────────────────────────────────────────


class TestExport:
    """测试 export() 方法和时间戳。"""

    def test_export_returns_dict(self):
        """验证 export() 返回字典。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        result = snapshot.export()
        assert isinstance(result, dict)

    def test_export_contains_all_required_fields(self):
        """验证 export() 包含所有必需字段。"""
        snapshot = MachineSnapshot(
            cpu_percent=45.2,
            mem_percent=68.5,
            mem_used_mb=8192,
            mem_total_mb=12288,
            swap_percent=10.0,
            disk_percent=75.3,
            disk_used_mb=512000,
            disk_total_mb=680000,
        )
        result = snapshot.export()
        assert "cpu_percent" in result
        assert "mem_percent" in result
        assert "mem_used_mb" in result
        assert "mem_total_mb" in result
        assert "swap_percent" in result
        assert "disk_percent" in result
        assert "disk_used_mb" in result
        assert "disk_total_mb" in result

    def test_export_contains_timestamp(self):
        """验证 export() 包含 timestamp 字段。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        result = snapshot.export()
        assert "timestamp" in result

    def test_export_timestamp_is_float(self):
        """验证 timestamp 为 float 类型（Unix 时间戳）。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        result = snapshot.export()
        assert isinstance(result["timestamp"], float)

    def test_export_timestamp_matches_created_at(self):
        """验证 timestamp 与 created_at 一致。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        result = snapshot.export()
        expected_timestamp = snapshot.created_at.timestamp()
        assert abs(result["timestamp"] - expected_timestamp) < 0.001

    def test_export_includes_optional_fields_when_set(self):
        """验证 export() 包含已设置的可选字段。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
            proc_mem_mb=256,
            proc_workers=8,
        )
        result = snapshot.export()
        assert "proc_mem_mb" in result
        assert result["proc_mem_mb"] == 256
        assert "proc_workers" in result
        assert result["proc_workers"] == 8

    def test_export_includes_optional_fields_when_none(self):
        """验证 export() 包含值为 None 的可选字段。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        result = snapshot.export()
        assert "proc_mem_mb" in result
        assert result["proc_mem_mb"] is None


# ── TestInheritance ───────────────────────────────────────────────────────────


class TestInheritance:
    """测试 BaseContext 继承特性。"""

    def test_has_id_field(self):
        """验证继承了 id 字段。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        assert hasattr(snapshot, "id")
        assert isinstance(snapshot.id, str)

    def test_has_created_at_field(self):
        """验证继承了 created_at 字段。"""
        snapshot = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        assert hasattr(snapshot, "created_at")
        assert isinstance(snapshot.created_at, datetime)

    def test_different_instances_have_different_ids(self):
        """验证不同实例具有不同的 ID。"""
        snapshot1 = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        snapshot2 = MachineSnapshot(
            cpu_percent=0,
            mem_percent=0,
            mem_used_mb=0,
            mem_total_mb=0,
            swap_percent=0,
            disk_percent=0,
            disk_used_mb=0,
            disk_total_mb=0,
        )
        assert snapshot1.id != snapshot2.id


# ── TestEdgeCases ─────────────────────────────────────────────────────────────


class TestEdgeCases:
    """测试边界情况和特殊值。"""

    def test_zero_values(self):
        """验证可以创建所有字段为 0 的快照。"""
        snapshot = MachineSnapshot(
            cpu_percent=0.0,
            mem_percent=0.0,
            mem_used_mb=0.0,
            mem_total_mb=0.0,
            swap_percent=0.0,
            disk_percent=0.0,
            disk_used_mb=0.0,
            disk_total_mb=0.0,
        )
        assert snapshot.cpu_percent == 0.0
        assert snapshot.mem_percent == 0.0

    def test_max_values(self):
        """验证可以创建字段为最大值的快照。"""
        snapshot = MachineSnapshot(
            cpu_percent=100.0,
            mem_percent=100.0,
            mem_used_mb=999999.9,
            mem_total_mb=999999.9,
            swap_percent=100.0,
            disk_percent=100.0,
            disk_used_mb=999999999.9,
            disk_total_mb=999999999.9,
        )
        assert snapshot.cpu_percent == 100.0
        assert snapshot.mem_percent == 100.0

    def test_fractional_values(self):
        """验证可以使用小数值。"""
        snapshot = MachineSnapshot(
            cpu_percent=45.678,
            mem_percent=68.123,
            mem_used_mb=8192.456,
            mem_total_mb=12288.789,
            swap_percent=10.234,
            disk_percent=75.345,
            disk_used_mb=512000.678,
            disk_total_mb=680000.901,
        )
        assert abs(snapshot.cpu_percent - 45.678) < 0.001
        assert abs(snapshot.mem_percent - 68.123) < 0.001
