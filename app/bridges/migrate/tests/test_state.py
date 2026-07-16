"""
综合测试：app.bridges.migrate.state

覆盖范围
--------
- TestBridgesMigrationStatus  枚举值检查
- TestBridgesMigrationState   状态转换、属性计算
- TestStateTransition         start/finish/fail/cancel 状态转换
- TestStateProperties         duration_seconds、started_at_repr 等属性
- TestExport                  export() 和 describe() 方法
"""

from __future__ import annotations

import json
import time

from app.bridges.migrate.request import BridgesMigrateRequest
from app.bridges.migrate.state import BridgesMigrationState, BridgesMigrationStatus

# ──────────────────────────────────────────────────────────────────────────────
# TestBridgesMigrationStatus
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgesMigrationStatus:
    def test_status_enum_has_pending(self):
        """测试状态枚举包含 PENDING。"""
        assert hasattr(BridgesMigrationStatus, "PENDING")
        assert BridgesMigrationStatus.PENDING.value == "PENDING"

    def test_status_enum_has_running(self):
        """测试状态枚举包含 RUNNING。"""
        assert hasattr(BridgesMigrationStatus, "RUNNING")
        assert BridgesMigrationStatus.RUNNING.value == "RUNNING"

    def test_status_enum_has_done(self):
        """测试状态枚举包含 DONE。"""
        assert hasattr(BridgesMigrationStatus, "DONE")
        assert BridgesMigrationStatus.DONE.value == "DONE"

    def test_status_enum_has_failed(self):
        """测试状态枚举包含 FAILED。"""
        assert hasattr(BridgesMigrationStatus, "FAILED")
        assert BridgesMigrationStatus.FAILED.value == "FAILED"

    def test_status_enum_has_canceled(self):
        """测试状态枚举包含 CANCELED。"""
        assert hasattr(BridgesMigrationStatus, "CANCELED")
        assert BridgesMigrationStatus.CANCELED.value == "CANCELED"


# ──────────────────────────────────────────────────────────────────────────────
# TestBridgesMigrationState
# ──────────────────────────────────────────────────────────────────────────────


class TestBridgesMigrationState:
    def test_initial_status_is_pending(self):
        """测试初始状态为 PENDING。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        assert state.status == BridgesMigrationStatus.PENDING

    def test_initial_timestamps_are_none(self):
        """测试初始时间戳为 None。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        assert state.started_at is None
        assert state.finished_at is None

    def test_initial_error_is_none(self):
        """测试初始错误为 None。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        assert state.error is None

    def test_initial_rows_is_none(self):
        """测试初始行数为 None。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        assert state.rows is None


# ──────────────────────────────────────────────────────────────────────────────
# TestStateTransition
# ──────────────────────────────────────────────────────────────────────────────


class TestStateTransition:
    def test_start_changes_status_to_running(self):
        """测试 start() 改变状态为 RUNNING。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        assert state.status == BridgesMigrationStatus.RUNNING

    def test_start_sets_started_at(self):
        """测试 start() 设置 started_at。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        assert state.started_at is not None

    def test_finish_changes_status_to_done(self):
        """测试 finish() 改变状态为 DONE。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        state.finish(rows=1000)
        assert state.status == BridgesMigrationStatus.DONE

    def test_finish_sets_finished_at(self):
        """测试 finish() 设置 finished_at。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        state.finish(rows=1000)
        assert state.finished_at is not None

    def test_finish_sets_rows(self):
        """测试 finish() 设置 rows。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        state.finish(rows=1000)
        assert state.rows == 1000

    def test_fail_changes_status_to_failed(self):
        """测试 fail() 改变状态为 FAILED。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        state.fail("Connection timeout")
        assert state.status == BridgesMigrationStatus.FAILED

    def test_fail_sets_error_message(self):
        """测试 fail() 设置错误信息。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        state.fail("Connection timeout")
        assert state.error == "Connection timeout"

    def test_fail_sets_finished_at(self):
        """测试 fail() 设置 finished_at。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        state.fail("Connection timeout")
        assert state.finished_at is not None

    def test_cancel_changes_status_to_canceled(self):
        """测试 cancel() 改变状态为 CANCELED。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.cancel()
        assert state.status == BridgesMigrationStatus.CANCELED

    def test_cancel_sets_finished_at(self):
        """测试 cancel() 设置 finished_at。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.cancel()
        assert state.finished_at is not None

    def test_is_cancelled_returns_true_after_cancel(self):
        """测试 _is_cancelled() 在 cancel 后返回 True。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.cancel()
        assert state._is_cancelled() is True

    def test_is_cancelled_returns_false_before_cancel(self):
        """测试 _is_cancelled() 在 cancel 前返回 False。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        assert state._is_cancelled() is False


# ──────────────────────────────────────────────────────────────────────────────
# TestStateProperties
# ──────────────────────────────────────────────────────────────────────────────


class TestStateProperties:
    def test_duration_seconds_is_none_before_start(self):
        """测试开始前 duration_seconds 为 None。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        assert state.duration_seconds is None

    def test_duration_seconds_is_calculated_after_finish(self):
        """测试完成后 duration_seconds 被计算。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        time.sleep(0.1)  # 等待一小段时间
        state.finish(rows=1000)
        assert state.duration_seconds is not None
        assert state.duration_seconds >= 0.1

    def test_started_at_repr_returns_iso_format(self):
        """测试 started_at_repr 返回 ISO 格式字符串。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        assert state.started_at_repr is not None
        # ISO format contains 'T' separator
        assert "T" in state.started_at_repr

    def test_finished_at_repr_returns_iso_format(self):
        """测试 finished_at_repr 返回 ISO 格式字符串。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        state.finish(rows=1000)
        assert state.finished_at_repr is not None
        assert "T" in state.finished_at_repr

    def test_succeeded_is_true_when_done(self):
        """测试 succeeded 在 DONE 状态时为 True。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        state.finish(rows=1000)
        assert state.succeeded is True

    def test_succeeded_is_false_when_failed(self):
        """测试 succeeded 在 FAILED 状态时为 False。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        state.fail("Error occurred")
        assert state.succeeded is False


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    def test_export_returns_dict(self):
        """测试 export() 返回字典。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        exported = state.export()
        assert isinstance(exported, dict)

    def test_export_contains_request_id(self):
        """测试 export() 包含 request_id。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        exported = state.export()
        assert "request_id" in exported
        assert exported["request_id"] == request.id

    def test_export_contains_status(self):
        """测试 export() 包含 status。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        exported = state.export()
        assert "status" in exported
        assert exported["status"] == "PENDING"

    def test_export_contains_all_fields(self):
        """测试 export() 包含所有字段。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        state.start()
        state.finish(rows=1000)
        exported = state.export()
        assert "request_id" in exported
        assert "status" in exported
        assert "started_at" in exported
        assert "finished_at" in exported
        assert "duration_seconds" in exported
        assert "error" in exported
        assert "rows" in exported

    def test_describe_returns_json_string(self):
        """测试 describe() 返回 JSON 字符串。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        described = state.describe()
        assert isinstance(described, str)
        # 验证是否为有效的 JSON
        parsed = json.loads(described)
        assert isinstance(parsed, dict)

    def test_describe_contains_request_id(self):
        """测试 describe() 包含 request_id。"""
        request = BridgesMigrateRequest(
            source_name="test_source",
            from_destination="src_oss",
            from_glob="s3://bucket/prefix/**/*.parquet",
            to_destination="tgt_oss",
        )
        state = BridgesMigrationState(request=request)
        described = state.describe()
        parsed = json.loads(described)
        assert "request_id" in parsed
        assert parsed["request_id"] == request.id
