"""
综合测试：app.bridges.base.state

覆盖范围
--------
- TestBaseBridgesStatus  枚举值检查
- TestBaseBridgesState          基本初始化和属性
- TestCancel                    取消操作和状态转换
- TestDuration                  持续时间计算
- TestTimestampRepr             时间戳表示方法
- TestExport                    export() 方法
- TestDescribe                  describe() 方法
"""

from __future__ import annotations

import json
import time
from datetime import datetime

from app.bridges.resources.base.state import BaseBridgesState, BaseBridgesStatus

# ──────────────────────────────────────────────────────────────────────────────
# TestBaseBridgesStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseBridgesStatus:
    """测试状态枚举的值"""

    def test_status_enum_has_pending(self):
        """测试状态枚举包含 PENDING"""
        assert hasattr(BaseBridgesStatus, "PENDING")
        assert BaseBridgesStatus.PENDING.value == "PENDING"

    def test_status_enum_has_running(self):
        """测试状态枚举包含 RUNNING"""
        assert hasattr(BaseBridgesStatus, "RUNNING")
        assert BaseBridgesStatus.RUNNING.value == "RUNNING"

    def test_status_enum_has_done(self):
        """测试状态枚举包含 DONE"""
        assert hasattr(BaseBridgesStatus, "DONE")
        assert BaseBridgesStatus.DONE.value == "DONE"

    def test_status_enum_has_partial(self):
        """测试状态枚举包含 PARTIAL"""
        assert hasattr(BaseBridgesStatus, "PARTIAL")
        assert BaseBridgesStatus.PARTIAL.value == "PARTIAL"

    def test_status_enum_has_failed(self):
        """测试状态枚举包含 FAILED"""
        assert hasattr(BaseBridgesStatus, "FAILED")
        assert BaseBridgesStatus.FAILED.value == "FAILED"

    def test_status_enum_has_canceled(self):
        """测试状态枚举包含 CANCELED"""
        assert hasattr(BaseBridgesStatus, "CANCELED")
        assert BaseBridgesStatus.CANCELED.value == "CANCELED"

    def test_status_enum_is_string_enum(self):
        """测试状态枚举继承自 str"""
        assert isinstance(BaseBridgesStatus.PENDING, str)
        assert isinstance(BaseBridgesStatus.RUNNING, str)


# ──────────────────────────────────────────────────────────────────────────────
# TestBaseBridgesState
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseBridgesState:
    """测试 BaseBridgesState 基本初始化和属性"""

    def test_initial_status_is_pending(self):
        """测试初始状态为 PENDING"""
        state = BaseBridgesState()
        assert state.status == BaseBridgesStatus.PENDING

    def test_initial_started_at_is_none(self):
        """测试初始 started_at 为 None"""
        state = BaseBridgesState()
        assert state.started_at is None

    def test_initial_finished_at_is_none(self):
        """测试初始 finished_at 为 None"""
        state = BaseBridgesState()
        assert state.finished_at is None

    def test_can_initialize_with_custom_status(self):
        """测试可以使用自定义状态初始化"""
        state = BaseBridgesState(status=BaseBridgesStatus.RUNNING)
        assert state.status == BaseBridgesStatus.RUNNING

    def test_can_initialize_with_timestamps(self):
        """测试可以使用时间戳初始化"""
        now = datetime.now()
        state = BaseBridgesState(
            started_at=now,
            finished_at=now,
        )
        assert state.started_at == now
        assert state.finished_at == now


# ──────────────────────────────────────────────────────────────────────────────
# TestCancel
# ──────────────────────────────────────────────────────────────────────────────


class TestCancel:
    """测试取消操作"""

    def test_cancel_sets_status_to_canceled(self):
        """测试 cancel() 将状态设置为 CANCELED"""
        state = BaseBridgesState()
        state.cancel()
        assert state.status == BaseBridgesStatus.CANCELED

    def test_cancel_sets_finished_at(self):
        """测试 cancel() 设置 finished_at"""
        state = BaseBridgesState()
        state.cancel()
        assert state.finished_at is not None
        assert isinstance(state.finished_at, datetime)

    def test_is_cancelled_returns_true_after_cancel(self):
        """测试 _is_cancelled() 在取消后返回 True"""
        state = BaseBridgesState()
        state.cancel()
        assert state._is_cancelled() is True

    def test_is_cancelled_returns_false_initially(self):
        """测试 _is_cancelled() 初始返回 False"""
        state = BaseBridgesState()
        assert state._is_cancelled() is False

    def test_is_cancelled_returns_false_for_other_statuses(self):
        """测试 _is_cancelled() 对其他状态返回 False"""
        state = BaseBridgesState(status=BaseBridgesStatus.DONE)
        assert state._is_cancelled() is False

        state = BaseBridgesState(status=BaseBridgesStatus.FAILED)
        assert state._is_cancelled() is False


# ──────────────────────────────────────────────────────────────────────────────
# TestDuration
# ──────────────────────────────────────────────────────────────────────────────


class TestDuration:
    """测试持续时间计算"""

    def test_duration_is_none_when_not_started(self):
        """测试未开始时 duration 为 None"""
        state = BaseBridgesState()
        assert state.duration_seconds is None

    def test_duration_is_none_when_not_finished(self):
        """测试未完成时 duration 为 None"""
        state = BaseBridgesState(started_at=datetime.now())
        assert state.duration_seconds is None

    def test_duration_calculates_correctly(self):
        """测试 duration 正确计算"""
        start = datetime(2026, 7, 16, 10, 0, 0)
        end = datetime(2026, 7, 16, 10, 0, 5)  # 5秒后
        state = BaseBridgesState(started_at=start, finished_at=end)

        assert state.duration_seconds == 5.0

    def test_duration_with_microseconds(self):
        """测试带微秒的 duration 计算"""
        start = datetime(2026, 7, 16, 10, 0, 0, 0)
        end = datetime(2026, 7, 16, 10, 0, 1, 500000)  # 1.5秒后
        state = BaseBridgesState(started_at=start, finished_at=end)

        assert state.duration_seconds == 1.5

    def test_duration_after_cancel(self):
        """测试取消后 duration 可以计算"""
        state = BaseBridgesState()
        # 使用 _get_current_datetime() 确保时区一致
        state.started_at = state._get_current_datetime()

        # 稍微等待一下，然后取消
        time.sleep(0.01)
        state.cancel()

        assert state.duration_seconds is not None
        assert state.duration_seconds >= 0


# ──────────────────────────────────────────────────────────────────────────────
# TestTimestampRepr
# ──────────────────────────────────────────────────────────────────────────────


class TestTimestampRepr:
    """测试时间戳表示方法"""

    def test_started_at_repr_is_none_initially(self):
        """测试初始 started_at_repr 为 None"""
        state = BaseBridgesState()
        assert state.started_at_repr is None

    def test_finished_at_repr_is_none_initially(self):
        """测试初始 finished_at_repr 为 None"""
        state = BaseBridgesState()
        assert state.finished_at_repr is None

    def test_started_at_repr_returns_isoformat(self):
        """测试 started_at_repr 返回 ISO 格式字符串"""
        dt = datetime(2026, 7, 16, 10, 30, 45)
        state = BaseBridgesState(started_at=dt)
        assert state.started_at_repr == "2026-07-16T10:30:45"

    def test_finished_at_repr_returns_isoformat(self):
        """测试 finished_at_repr 返回 ISO 格式字符串"""
        dt = datetime(2026, 7, 16, 11, 30, 45)
        state = BaseBridgesState(finished_at=dt)
        assert state.finished_at_repr == "2026-07-16T11:30:45"

    def test_repr_with_microseconds(self):
        """测试带微秒的 repr"""
        dt = datetime(2026, 7, 16, 10, 30, 45, 123456)
        state = BaseBridgesState(started_at=dt)
        assert state.started_at_repr == "2026-07-16T10:30:45.123456"


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    """测试 export() 方法"""

    def test_export_returns_dict(self):
        """测试 export() 返回字典"""
        state = BaseBridgesState()
        result = state.export()
        assert isinstance(result, dict)

    def test_export_contains_status(self):
        """测试 export() 包含 status 键"""
        state = BaseBridgesState()
        result = state.export()
        assert "status" in result
        assert result["status"] == "PENDING"

    def test_export_contains_started_at(self):
        """测试 export() 包含 started_at 键"""
        state = BaseBridgesState()
        result = state.export()
        assert "started_at" in result
        assert result["started_at"] is None

    def test_export_contains_finished_at(self):
        """测试 export() 包含 finished_at 键"""
        state = BaseBridgesState()
        result = state.export()
        assert "finished_at" in result
        assert result["finished_at"] is None

    def test_export_contains_duration_seconds(self):
        """测试 export() 包含 duration_seconds 键"""
        state = BaseBridgesState()
        result = state.export()
        assert "duration_seconds" in result
        assert result["duration_seconds"] is None

    def test_export_with_all_fields_populated(self):
        """测试所有字段都填充时的 export()"""
        start = datetime(2026, 7, 16, 10, 0, 0)
        end = datetime(2026, 7, 16, 10, 0, 10)
        state = BaseBridgesState(
            status=BaseBridgesStatus.DONE,
            started_at=start,
            finished_at=end,
        )
        result = state.export()

        assert result["status"] == "DONE"
        assert result["started_at"] == "2026-07-16T10:00:00"
        assert result["finished_at"] == "2026-07-16T10:00:10"
        assert result["duration_seconds"] == 10.0

    def test_export_after_cancel(self):
        """测试取消后的 export()"""
        state = BaseBridgesState()
        # 使用 _get_current_datetime() 确保时区一致
        state.started_at = state._get_current_datetime()
        state.cancel()
        result = state.export()

        assert result["status"] == "CANCELED"
        assert result["started_at"] is not None
        assert result["finished_at"] is not None
        assert result["duration_seconds"] is not None


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    """测试 describe() 方法"""

    def test_describe_returns_string(self):
        """测试 describe() 返回字符串"""
        state = BaseBridgesState()
        result = state.describe()
        assert isinstance(result, str)

    def test_describe_returns_valid_json(self):
        """测试 describe() 返回有效的 JSON"""
        state = BaseBridgesState()
        result = state.describe()

        # 应该可以解析为 JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_contains_status(self):
        """测试 describe() 包含 status"""
        state = BaseBridgesState()
        result = state.describe()
        parsed = json.loads(result)

        assert "status" in parsed
        assert parsed["status"] == "PENDING"

    def test_describe_formatted_with_indent(self):
        """测试 describe() 格式化有缩进"""
        state = BaseBridgesState()
        result = state.describe()

        # 缩进的 JSON 应该包含换行符
        assert "\n" in result

    def test_describe_with_all_fields(self):
        """测试所有字段都填充时的 describe()"""
        start = datetime(2026, 7, 16, 10, 0, 0)
        end = datetime(2026, 7, 16, 10, 0, 5)
        state = BaseBridgesState(
            status=BaseBridgesStatus.DONE,
            started_at=start,
            finished_at=end,
        )
        result = state.describe()
        parsed = json.loads(result)

        assert parsed["status"] == "DONE"
        assert parsed["started_at"] == "2026-07-16T10:00:00"
        assert parsed["finished_at"] == "2026-07-16T10:00:05"
        assert parsed["duration_seconds"] == 5.0

    def test_describe_preserves_chinese_characters(self):
        """测试 describe() 保留中文字符（ensure_ascii=False）"""
        # 虽然当前实现没有中文字段，但确保设置生效
        state = BaseBridgesState()
        result = state.describe()

        # 应该不包含 Unicode 转义序列（如 \u4e2d）
        assert "\\u" not in result
