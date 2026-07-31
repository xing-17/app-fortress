"""
综合测试：app.bridges.base.servicehealth

覆盖范围
--------
- TestInstantiation       基本实例化和字段验证
- TestQueueUsage          queue_usage 属性计算
- TestIdleSeconds         idle_seconds 属性计算
- TestExport              export() 方法完整性
- TestEdgeCases           边界情况和 None 值处理
"""

from __future__ import annotations

import time
from time import monotonic

from app.bridges.base.servicehealth import ServiceHealth

# ──────────────────────────────────────────────────────────────────────────────
# TestInstantiation
# ──────────────────────────────────────────────────────────────────────────────


class TestInstantiation:
    """测试基本实例化和字段验证"""

    def test_can_instantiate_with_service_name(self):
        """测试可以使用服务名称实例化"""
        health = ServiceHealth(service="test_service")
        assert health.service == "test_service"

    def test_id_has_correct_prefix(self):
        """测试 ID 使用正确的前缀"""
        health = ServiceHealth(service="test")
        assert health.id.startswith("svch-")

    def test_can_set_worker_name(self):
        """测试可以设置工作线程名称"""
        health = ServiceHealth(service="test", worker_name="TestWorker")
        assert health.worker_name == "TestWorker"

    def test_can_set_worker_alive(self):
        """测试可以设置工作线程存活状态"""
        health = ServiceHealth(service="test", worker_alive=True)
        assert health.worker_alive is True

    def test_can_set_worker_daemon(self):
        """测试可以设置工作线程守护状态"""
        health = ServiceHealth(service="test", worker_daemon=True)
        assert health.worker_daemon is True

    def test_can_set_worker_ident(self):
        """测试可以设置工作线程标识符"""
        health = ServiceHealth(service="test", worker_ident=12345)
        assert health.worker_ident == 12345

    def test_can_set_worker_native_id(self):
        """测试可以设置工作线程原生标识符"""
        health = ServiceHealth(service="test", worker_native_id=67890)
        assert health.worker_native_id == 67890

    def test_can_set_worker_count(self):
        """测试可以设置工作线程计数"""
        health = ServiceHealth(service="test", worker_count=5)
        assert health.worker_count == 5

    def test_can_set_queue_size(self):
        """测试可以设置队列大小"""
        health = ServiceHealth(service="test", queue_size=10)
        assert health.queue_size == 10

    def test_can_set_queue_limit(self):
        """测试可以设置队列限制"""
        health = ServiceHealth(service="test", queue_limit=100)
        assert health.queue_limit == 100

    def test_can_set_queue_full(self):
        """测试可以设置队列是否已满"""
        health = ServiceHealth(service="test", queue_full=False)
        assert health.queue_full is False

    def test_can_set_last_active_time(self):
        """测试可以设置最后活跃时间"""
        now = monotonic()
        health = ServiceHealth(service="test", last_active_time=now)
        assert health.last_active_time == now

    def test_default_values_are_none(self):
        """测试默认值为 None"""
        health = ServiceHealth(service="test")
        assert health.worker_name is None
        assert health.worker_alive is None
        assert health.worker_daemon is None
        assert health.worker_ident is None
        assert health.worker_native_id is None
        assert health.worker_count is None
        assert health.queue_size is None
        assert health.queue_limit is None
        assert health.queue_full is None
        assert health.last_active_time is None


# ──────────────────────────────────────────────────────────────────────────────
# TestQueueUsage
# ──────────────────────────────────────────────────────────────────────────────


class TestQueueUsage:
    """测试 queue_usage 属性计算"""

    def test_queue_usage_calculates_correctly(self):
        """测试队列使用率计算正确"""
        health = ServiceHealth(
            service="test",
            queue_size=25,
            queue_limit=100,
        )
        assert health.queue_usage == 0.25

    def test_queue_usage_full_queue(self):
        """测试队列满时使用率为 1.0"""
        health = ServiceHealth(
            service="test",
            queue_size=100,
            queue_limit=100,
        )
        assert health.queue_usage == 1.0

    def test_queue_usage_empty_queue(self):
        """测试队列空时使用率为 0.0"""
        health = ServiceHealth(
            service="test",
            queue_size=0,
            queue_limit=100,
        )
        assert health.queue_usage == 0.0

    def test_queue_usage_returns_zero_when_limit_is_none(self):
        """测试 queue_limit 为 None 时返回 0.0"""
        health = ServiceHealth(
            service="test",
            queue_size=10,
            queue_limit=None,
        )
        assert health.queue_usage == 0.0

    def test_queue_usage_returns_zero_when_limit_is_zero(self):
        """测试 queue_limit 为 0 时返回 0.0"""
        health = ServiceHealth(
            service="test",
            queue_size=10,
            queue_limit=0,
        )
        assert health.queue_usage == 0.0

    def test_queue_usage_rounds_to_4_decimals(self):
        """测试队列使用率四舍五入到 4 位小数"""
        health = ServiceHealth(
            service="test",
            queue_size=1,
            queue_limit=3,
        )
        # 1/3 = 0.333333...
        assert health.queue_usage == 0.3333

    def test_queue_usage_with_partial_values(self):
        """测试部分数值的队列使用率"""
        health = ServiceHealth(
            service="test",
            queue_size=37,
            queue_limit=200,
        )
        assert health.queue_usage == 0.185


# ──────────────────────────────────────────────────────────────────────────────
# TestIdleSeconds
# ──────────────────────────────────────────────────────────────────────────────


class TestIdleSeconds:
    """测试 idle_seconds 属性计算"""

    def test_idle_seconds_returns_none_when_last_active_time_is_none(self):
        """测试 last_active_time 为 None 时返回 None"""
        health = ServiceHealth(service="test")
        assert health.idle_seconds is None

    def test_idle_seconds_calculates_correctly(self):
        """测试空闲秒数计算正确"""
        past_time = monotonic() - 5.0  # 5 秒前
        health = ServiceHealth(service="test", last_active_time=past_time)
        idle = health.idle_seconds

        assert idle is not None
        assert idle >= 5.0  # 至少 5 秒
        assert idle < 5.5  # 但不应超过 5.5 秒（给一些误差范围）

    def test_idle_seconds_increases_over_time(self):
        """测试空闲秒数随时间增加"""
        past_time = monotonic() - 2.0  # 2 秒前
        health = ServiceHealth(service="test", last_active_time=past_time)

        first_idle = health.idle_seconds
        time.sleep(0.1)  # 等待 100ms
        second_idle = health.idle_seconds

        assert second_idle > first_idle

    def test_idle_seconds_rounds_to_2_decimals(self):
        """测试空闲秒数四舍五入到 2 位小数"""
        past_time = monotonic() - 1.23456
        health = ServiceHealth(service="test", last_active_time=past_time)
        idle = health.idle_seconds

        assert idle is not None
        # 检查小数位数不超过 2 位
        decimal_places = len(str(idle).split(".")[-1]) if "." in str(idle) else 0
        assert decimal_places <= 2

    def test_idle_seconds_with_recent_activity(self):
        """测试最近活跃的空闲秒数"""
        recent_time = monotonic() - 0.1  # 100ms 前
        health = ServiceHealth(service="test", last_active_time=recent_time)
        idle = health.idle_seconds

        assert idle is not None
        assert idle >= 0.1
        assert idle < 0.5


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    """测试 export() 方法"""

    def test_export_returns_dict(self):
        """测试 export() 返回字典"""
        health = ServiceHealth(service="test")
        result = health.export()
        assert isinstance(result, dict)

    def test_export_contains_service_name(self):
        """测试导出包含服务名称"""
        health = ServiceHealth(service="my_service")
        result = health.export()
        assert result["service"] == "my_service"

    def test_export_contains_last_active_time(self):
        """测试导出包含最后活跃时间"""
        now = monotonic()
        health = ServiceHealth(service="test", last_active_time=now)
        result = health.export()
        assert result["last_active_time"] == now

    def test_export_contains_idle_seconds(self):
        """测试导出包含空闲秒数"""
        past_time = monotonic() - 5.0
        health = ServiceHealth(service="test", last_active_time=past_time)
        result = health.export()
        assert "idle_seconds" in result
        assert result["idle_seconds"] >= 5.0

    def test_export_contains_worker_section(self):
        """测试导出包含工作线程部分"""
        health = ServiceHealth(
            service="test",
            worker_name="TestWorker",
            worker_alive=True,
            worker_daemon=False,
            worker_ident=123,
            worker_native_id=456,
            worker_count=3,
        )
        result = health.export()

        assert "worker" in result
        assert isinstance(result["worker"], dict)
        assert result["worker"]["name"] == "TestWorker"
        assert result["worker"]["alive"] is True
        assert result["worker"]["daemon"] is False
        assert result["worker"]["ident"] == 123
        assert result["worker"]["native_id"] == 456
        assert result["worker"]["count"] == 3

    def test_export_contains_queue_section(self):
        """测试导出包含队列部分"""
        health = ServiceHealth(
            service="test",
            queue_size=50,
            queue_limit=100,
            queue_full=False,
        )
        result = health.export()

        assert "queue" in result
        assert isinstance(result["queue"], dict)
        assert result["queue"]["size"] == 50
        assert result["queue"]["limit"] == 100
        assert result["queue"]["full"] is False
        assert result["queue"]["usage"] == 0.5

    def test_export_with_all_fields(self):
        """测试导出所有字段"""
        now = monotonic()
        health = ServiceHealth(
            service="comprehensive_service",
            worker_name="Worker-1",
            worker_alive=True,
            worker_daemon=True,
            worker_ident=111,
            worker_native_id=222,
            worker_count=5,
            queue_size=25,
            queue_limit=100,
            queue_full=False,
            last_active_time=now,
        )
        result = health.export()

        # 验证顶层键
        assert "service" in result
        assert "last_active_time" in result
        assert "idle_seconds" in result
        assert "worker" in result
        assert "queue" in result

        # 验证所有值都已填充
        assert result["service"] == "comprehensive_service"
        assert result["last_active_time"] == now
        assert result["worker"]["name"] == "Worker-1"
        assert result["queue"]["size"] == 25

    def test_export_with_none_values(self):
        """测试导出时 None 值处理"""
        health = ServiceHealth(service="test")
        result = health.export()

        # 验证结构完整，即使值为 None
        assert result["worker"]["name"] is None
        assert result["worker"]["alive"] is None
        assert result["queue"]["size"] is None
        assert result["last_active_time"] is None
        assert result["idle_seconds"] is None


# ──────────────────────────────────────────────────────────────────────────────
# TestEdgeCases
# ──────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """测试边界情况和特殊场景"""

    def test_queue_full_flag_matches_actual_usage(self):
        """测试 queue_full 标志与实际使用率一致"""
        # 队列已满
        health_full = ServiceHealth(
            service="test",
            queue_size=100,
            queue_limit=100,
            queue_full=True,
        )
        assert health_full.queue_full is True
        assert health_full.queue_usage == 1.0

        # 队列未满
        health_not_full = ServiceHealth(
            service="test",
            queue_size=50,
            queue_limit=100,
            queue_full=False,
        )
        assert health_not_full.queue_full is False
        assert health_not_full.queue_usage < 1.0

    def test_worker_alive_false_indicates_stopped_service(self):
        """测试 worker_alive=False 表示服务已停止"""
        health = ServiceHealth(
            service="stopped_service",
            worker_alive=False,
            queue_size=0,
        )
        assert health.worker_alive is False

    def test_negative_idle_time_not_possible(self):
        """测试空闲时间不可能为负（理论上）"""
        # 使用当前时间，空闲时间应该非常接近 0
        now = monotonic()
        health = ServiceHealth(service="test", last_active_time=now)
        idle = health.idle_seconds

        assert idle is not None
        assert idle >= 0.0

    def test_large_queue_values(self):
        """测试大队列值"""
        health = ServiceHealth(
            service="test",
            queue_size=999999,
            queue_limit=1000000,
        )
        # 999999 / 1000000 = 0.999999，四舍五入到 4 位是 1.0
        assert health.queue_usage == 1.0

    def test_zero_worker_count(self):
        """测试工作线程数为 0"""
        health = ServiceHealth(
            service="test",
            worker_count=0,
        )
        assert health.worker_count == 0

    def test_multiple_health_instances_independent(self):
        """测试多个健康实例相互独立"""
        health1 = ServiceHealth(service="service1", queue_size=10)
        health2 = ServiceHealth(service="service2", queue_size=20)

        assert health1.service != health2.service
        assert health1.queue_size != health2.queue_size
        assert health1.id != health2.id
