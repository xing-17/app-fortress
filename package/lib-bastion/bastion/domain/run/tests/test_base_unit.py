"""
Unit tests for bastion.domain.run.base module.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from bastion.domain.run.base import BaseRunModel, RunStatus


class TestRunStatus:
    """Test RunStatus enumeration."""

    def test_run_status_values(self):
        """Test RunStatus has all correct values."""
        assert RunStatus.PENDING == "pending"
        assert RunStatus.RUNNING == "running"
        assert RunStatus.SUCCEEDED == "succeeded"
        assert RunStatus.FAILED == "failed"
        assert RunStatus.CANCELLED == "cancelled"

    def test_from_any_with_run_status(self):
        """Test from_any returns same RunStatus instance."""
        status = RunStatus.RUNNING
        result = RunStatus.from_any(status)
        assert result == status
        assert result is status

    def test_from_any_with_valid_string(self):
        """Test from_any converts valid string to RunStatus."""
        result = RunStatus.from_any("pending")
        assert result == RunStatus.PENDING
        assert isinstance(result, RunStatus)

    def test_from_any_with_invalid_string(self):
        """Test from_any raises ValueError for invalid string."""
        with pytest.raises(ValueError, match="Invalid RunStatus value: invalid"):
            RunStatus.from_any("invalid")


class TestBaseRunModel:
    """Test BaseRunModel class."""

    def test_create_base_run_model(self):
        """Test creating a basic run model."""
        run = BaseRunModel(bridge_name="test_bridge")
        assert run.bridge_name == "test_bridge"
        assert run.status == RunStatus.PENDING
        assert isinstance(run.created_at, datetime)
        assert run.started_at is None
        assert run.finished_at is None
        assert run.id != ""

    def test_id_generation(self):
        """Test that runs have unique IDs with correct prefix."""
        run1 = BaseRunModel(bridge_name="bridge1")
        run2 = BaseRunModel(bridge_name="bridge2")

        assert run1.id != run2.id
        assert run1.id.startswith("run-")
        assert run2.id.startswith("run-")
        assert len(run1.id.split("-")[1]) == 16

    def test_missing_bridge_name_raises(self):
        """Test creating run without bridge_name raises error."""
        with pytest.raises(ValidationError):
            BaseRunModel()

    def test_start_method(self):
        """Test start() sets status to RUNNING and started_at."""
        run = BaseRunModel(bridge_name="test_bridge")
        run.start()

        assert run.status == RunStatus.RUNNING
        assert run.started_at is not None
        assert isinstance(run.started_at, datetime)

    def test_succeed_method(self):
        """Test succeed() sets status to SUCCEEDED and finished_at."""
        run = BaseRunModel(bridge_name="test_bridge")
        run.start()
        run.succeed()

        assert run.status == RunStatus.SUCCEEDED
        assert run.finished_at is not None
        assert isinstance(run.finished_at, datetime)

    def test_fail_method(self):
        """Test fail() sets status to FAILED and finished_at."""
        run = BaseRunModel(bridge_name="test_bridge")
        run.start()
        run.fail()

        assert run.status == RunStatus.FAILED
        assert run.finished_at is not None
        assert isinstance(run.finished_at, datetime)

    def test_cancel_method(self):
        """Test cancel() sets status to CANCELLED and finished_at."""
        run = BaseRunModel(bridge_name="test_bridge")
        run.cancel()

        assert run.status == RunStatus.CANCELLED
        assert run.finished_at is not None
        assert isinstance(run.finished_at, datetime)

    def test_full_success_workflow(self):
        """Test complete success workflow."""
        run = BaseRunModel(bridge_name="test_bridge")
        assert run.status == RunStatus.PENDING

        run.start()
        assert run.status == RunStatus.RUNNING
        assert run.started_at is not None

        run.succeed()
        assert run.status == RunStatus.SUCCEEDED
        assert run.finished_at is not None

    def test_full_failure_workflow(self):
        """Test complete failure workflow."""
        run = BaseRunModel(bridge_name="test_bridge")
        assert run.status == RunStatus.PENDING

        run.start()
        assert run.status == RunStatus.RUNNING

        run.fail()
        assert run.status == RunStatus.FAILED
        assert run.finished_at is not None

    def test_export_method(self):
        """Test export() returns correct dictionary structure."""
        run = BaseRunModel(bridge_name="test_bridge")
        exported = run.export()

        assert isinstance(exported, dict)
        assert exported["id"] == run.id
        assert exported["bridge_name"] == "test_bridge"
        assert exported["status"] == "pending"
        assert isinstance(exported["created_at"], str)
        assert exported["started_at"] is None
        assert exported["finished_at"] is None

    def test_export_with_timestamps(self):
        """Test export() includes timestamps after state transitions."""
        run = BaseRunModel(bridge_name="test_bridge")
        run.start()
        run.succeed()
        exported = run.export()

        assert isinstance(exported["created_at"], str)
        assert isinstance(exported["started_at"], str)
        assert isinstance(exported["finished_at"], str)

        # Verify ISO format
        datetime.fromisoformat(exported["created_at"])
        datetime.fromisoformat(exported["started_at"])
        datetime.fromisoformat(exported["finished_at"])

    def test_export_status_is_string_value(self):
        """Test exported status is string value not enum."""
        run = BaseRunModel(bridge_name="test_bridge")
        run.start()
        exported = run.export()

        assert exported["status"] == "running"
        assert isinstance(exported["status"], str)
