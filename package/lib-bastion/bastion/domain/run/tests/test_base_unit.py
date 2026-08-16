"""
Unit tests for bastion.domain.run.base module.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from bastion.domain.event.base import BaseEventModel
from bastion.domain.quality.base import BaseQualityModel
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

    def test_from_any_with_string(self):
        """Test from_any converts string to RunStatus."""
        assert RunStatus("pending") == RunStatus.PENDING
        assert RunStatus("running") == RunStatus.RUNNING
        assert RunStatus("succeeded") == RunStatus.SUCCEEDED
        assert RunStatus("failed") == RunStatus.FAILED
        assert RunStatus("cancelled") == RunStatus.CANCELLED


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
        assert run.events == []
        assert run.qualities == []

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
        assert exported["events"] == []
        assert exported["qualities"] == []

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

    def test_from_any_with_dict(self):
        """Test from_any creates model from dictionary."""
        data = {
            "id": "run-abc123def456",
            "bridge_name": "test_bridge",
            "status": "running",
            "created_at": "2026-08-14T10:00:00",
            "started_at": "2026-08-14T10:00:01",
            "finished_at": None,
        }
        run = BaseRunModel.from_any(data)
        assert run.id == "run-abc123def456"
        assert run.bridge_name == "test_bridge"
        assert run.status == RunStatus.RUNNING
        assert run.created_at.year == 2026
        assert run.created_at.month == 8
        assert run.created_at.day == 14
        assert run.started_at is not None
        assert run.finished_at is None

    def test_roundtrip_export_from_any(self):
        """Test export and from_any roundtrip conversion."""
        original = BaseRunModel(bridge_name="roundtrip_bridge")
        original.start()
        original.succeed()

        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = BaseRunModel.from_any(exported)

        # Verify all fields match
        assert restored.id == original.id
        assert restored.bridge_name == original.bridge_name
        assert restored.status == original.status
        assert restored.created_at == original.created_at
        assert restored.started_at == original.started_at
        assert restored.finished_at == original.finished_at
        assert restored.events == []
        assert restored.qualities == []


class TestBaseRunModelEventsAndQualities:
    """Test BaseRunModel with events and qualities."""

    def test_events_field_defaults_to_empty_list(self):
        """Test events field defaults to empty list."""
        run = BaseRunModel(bridge_name="test_bridge")
        assert run.events == []
        assert isinstance(run.events, list)

    def test_qualities_field_defaults_to_empty_list(self):
        """Test qualities field defaults to empty list."""
        run = BaseRunModel(bridge_name="test_bridge")
        assert run.qualities == []
        assert isinstance(run.qualities, list)

    def test_create_run_with_events(self):
        """Test creating run with events."""
        run = BaseRunModel(bridge_name="test_bridge")
        event1 = BaseEventModel(run_id=run.id, message="Event 1")
        event2 = BaseEventModel(run_id=run.id, message="Event 2")

        run.events.append(event1)
        run.events.append(event2)

        assert len(run.events) == 2
        assert run.events[0].message == "Event 1"
        assert run.events[1].message == "Event 2"

    def test_create_run_with_qualities(self):
        """Test creating run with qualities."""
        run = BaseRunModel(bridge_name="test_bridge")
        quality1 = BaseQualityModel(run_id=run.id, passed=True, metrics={"count": 100})
        quality2 = BaseQualityModel(run_id=run.id, passed=False, metrics={"error_rate": 0.05})

        run.qualities.append(quality1)
        run.qualities.append(quality2)

        assert len(run.qualities) == 2
        assert run.qualities[0].passed is True
        assert run.qualities[1].passed is False

    def test_export_with_events(self):
        """Test export includes events."""
        run = BaseRunModel(bridge_name="test_bridge")
        event = BaseEventModel(run_id=run.id, message="test event")
        run.events.append(event)

        exported = run.export()

        assert "events" in exported
        assert len(exported["events"]) == 1
        assert exported["events"][0]["message"] == "test event"
        assert exported["events"][0]["run_id"] == run.id

    def test_export_with_qualities(self):
        """Test export includes qualities."""
        run = BaseRunModel(bridge_name="test_bridge")
        quality = BaseQualityModel(run_id=run.id, passed=True, metrics={"score": 95})
        run.qualities.append(quality)

        exported = run.export()

        assert "qualities" in exported
        assert len(exported["qualities"]) == 1
        assert exported["qualities"][0]["passed"] is True
        assert exported["qualities"][0]["metrics"]["score"] == 95

    def test_export_with_multiple_events_and_qualities(self):
        """Test export with multiple events and qualities."""
        run = BaseRunModel(bridge_name="test_bridge")

        # Add multiple events
        for i in range(3):
            event = BaseEventModel(run_id=run.id, message=f"Event {i}")
            run.events.append(event)

        # Add multiple qualities
        for i in range(2):
            quality = BaseQualityModel(run_id=run.id, passed=True, metrics={"iteration": i})
            run.qualities.append(quality)

        exported = run.export()

        assert len(exported["events"]) == 3
        assert len(exported["qualities"]) == 2

    def test_from_any_with_events_as_dicts(self):
        """Test from_any handles events as dict list."""
        data = {
            "id": "run-test123",
            "bridge_name": "test_bridge",
            "status": "pending",
            "created_at": "2026-08-16T10:00:00",
            "events": [
                {
                    "id": "event-abc123",
                    "run_id": "run-test123",
                    "message": "Test event",
                    "created_at": "2026-08-16T10:00:01",
                    "metadata": {},
                }
            ],
            "qualities": [],
        }

        run = BaseRunModel.from_any(data)

        assert len(run.events) == 1
        assert isinstance(run.events[0], BaseEventModel)
        assert run.events[0].message == "Test event"

    def test_from_any_with_qualities_as_dicts(self):
        """Test from_any handles qualities as dict list."""
        data = {
            "id": "run-test123",
            "bridge_name": "test_bridge",
            "status": "pending",
            "created_at": "2026-08-16T10:00:00",
            "events": [],
            "qualities": [
                {
                    "id": "qual-xyz789",
                    "run_id": "run-test123",
                    "kind": "base",
                    "passed": True,
                    "created_at": "2026-08-16T10:00:02",
                    "metrics": {"count": 100},
                }
            ],
        }

        run = BaseRunModel.from_any(data)

        assert len(run.qualities) == 1
        assert isinstance(run.qualities[0], BaseQualityModel)
        assert run.qualities[0].passed is True
        assert run.qualities[0].metrics["count"] == 100

    def test_from_any_handles_none_events(self):
        """Test from_any handles None for events field."""
        data = {"bridge_name": "test_bridge", "events": None, "qualities": []}

        run = BaseRunModel.from_any(data)
        assert run.events == []

    def test_from_any_handles_none_qualities(self):
        """Test from_any handles None for qualities field."""
        data = {"bridge_name": "test_bridge", "events": [], "qualities": None}

        run = BaseRunModel.from_any(data)
        assert run.qualities == []

    def test_from_any_handles_missing_events_and_qualities(self):
        """Test from_any handles missing events and qualities fields."""
        data = {"bridge_name": "test_bridge", "status": "pending"}

        run = BaseRunModel.from_any(data)
        assert run.events == []
        assert run.qualities == []

    def test_roundtrip_with_events(self):
        """Test full roundtrip with events."""
        # Create original run with events
        original = BaseRunModel(bridge_name="roundtrip_bridge")
        event1 = BaseEventModel(run_id=original.id, message="Start processing")
        event2 = BaseEventModel(
            run_id=original.id, message="Processing complete", metadata={"duration": "5s"}
        )
        original.events.append(event1)
        original.events.append(event2)
        original.start()
        original.succeed()

        # Export to dict
        exported = original.export()

        # Recreate from dict
        restored = BaseRunModel.from_any(exported)

        # Verify all fields match
        assert restored.id == original.id
        assert restored.bridge_name == original.bridge_name
        assert restored.status == original.status
        assert len(restored.events) == 2
        assert restored.events[0].message == "Start processing"
        assert restored.events[1].message == "Processing complete"
        assert restored.events[1].metadata["duration"] == "5s"

    def test_roundtrip_with_qualities(self):
        """Test full roundtrip with qualities."""
        # Create original run with qualities
        original = BaseRunModel(bridge_name="roundtrip_bridge")
        quality1 = BaseQualityModel(
            run_id=original.id,
            passed=True,
            description="Data validation",
            metrics={"rows": 1000, "nulls": 0},
        )
        quality2 = BaseQualityModel(
            run_id=original.id, passed=True, description="Schema check", metrics={"columns": 10}
        )
        original.qualities.append(quality1)
        original.qualities.append(quality2)
        original.start()
        original.succeed()

        # Export to dict
        exported = original.export()

        # Recreate from dict
        restored = BaseRunModel.from_any(exported)

        # Verify all fields match
        assert restored.id == original.id
        assert len(restored.qualities) == 2
        assert restored.qualities[0].description == "Data validation"
        assert restored.qualities[0].metrics["rows"] == 1000
        assert restored.qualities[1].description == "Schema check"

    def test_roundtrip_with_events_and_qualities(self):
        """Test full roundtrip with both events and qualities."""
        # Create original run with both events and qualities
        original = BaseRunModel(bridge_name="complete_roundtrip")

        # Add events
        event = BaseEventModel(
            run_id=original.id,
            message="Processing started",
            metadata={"timestamp": "2026-08-16T10:00:00"},
        )
        original.events.append(event)

        # Add qualities
        quality = BaseQualityModel(
            run_id=original.id,
            passed=True,
            description="Quality check passed",
            metrics={"accuracy": 0.95},
        )
        original.qualities.append(quality)

        # Run workflow
        original.start()
        original.succeed()

        # Export to dict
        exported = original.export()

        # Verify exported structure
        assert "events" in exported
        assert "qualities" in exported
        assert len(exported["events"]) == 1
        assert len(exported["qualities"]) == 1

        # Recreate from dict
        restored = BaseRunModel.from_any(exported)

        # Verify complete restoration
        assert restored.id == original.id
        assert restored.bridge_name == original.bridge_name
        assert restored.status == RunStatus.SUCCEEDED
        assert restored.started_at == original.started_at
        assert restored.finished_at == original.finished_at

        # Verify events restored
        assert len(restored.events) == 1
        assert isinstance(restored.events[0], BaseEventModel)
        assert restored.events[0].message == "Processing started"
        assert restored.events[0].metadata["timestamp"] == "2026-08-16T10:00:00"

        # Verify qualities restored
        assert len(restored.qualities) == 1
        assert isinstance(restored.qualities[0], BaseQualityModel)
        assert restored.qualities[0].passed is True
        assert restored.qualities[0].description == "Quality check passed"
        assert restored.qualities[0].metrics["accuracy"] == 0.95

    def test_roundtrip_preserves_event_and_quality_ids(self):
        """Test roundtrip preserves event and quality IDs."""
        # Create run with events and qualities
        original = BaseRunModel(bridge_name="id_preservation_test")

        event = BaseEventModel(run_id=original.id, message="Test event")
        quality = BaseQualityModel(run_id=original.id, passed=True)

        original.events.append(event)
        original.qualities.append(quality)

        event_id = event.id
        quality_id = quality.id

        # Roundtrip
        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        # Verify IDs are preserved
        assert restored.events[0].id == event_id
        assert restored.qualities[0].id == quality_id

    def test_multiple_roundtrips(self):
        """Test multiple consecutive roundtrips maintain data integrity."""
        # Create original
        original = BaseRunModel(bridge_name="multi_roundtrip")
        event = BaseEventModel(run_id=original.id, message="Test")
        quality = BaseQualityModel(run_id=original.id, passed=True, metrics={"x": 1})
        original.events.append(event)
        original.qualities.append(quality)

        # First roundtrip
        exported1 = original.export()
        restored1 = BaseRunModel.from_any(exported1)

        # Second roundtrip
        exported2 = restored1.export()
        restored2 = BaseRunModel.from_any(exported2)

        # Third roundtrip
        exported3 = restored2.export()
        restored3 = BaseRunModel.from_any(exported3)

        # Verify data integrity after multiple roundtrips
        assert restored3.id == original.id
        assert len(restored3.events) == 1
        assert len(restored3.qualities) == 1
        assert restored3.events[0].message == "Test"
        assert restored3.qualities[0].metrics["x"] == 1


class TestBaseRunModelDataInitialization:
    """
    Test BaseRunModel initialization with various data sets.
    Verify that any data set produces the expected model.
    """

    def test_minimal_dataset_only_required_fields(self):
        """Test initialization with minimal dataset (only bridge_name)."""
        data = {"bridge_name": "test_bridge"}
        run = BaseRunModel.from_any(data)

        assert run.bridge_name == "test_bridge"
        assert run.status == RunStatus.PENDING
        assert run.name is None
        assert run.created_at is not None
        assert run.started_at is None
        assert run.finished_at is None
        assert run.events == []
        assert run.qualities == []
        assert run.id.startswith("run-")

    def test_full_dataset_all_fields_provided(self):
        """Test initialization with complete dataset."""
        data = {
            "id": "run-complete123456",
            "bridge_name": "full_bridge",
            "name": "Full Test Run",
            "status": "succeeded",
            "created_at": "2026-08-16T10:00:00",
            "started_at": "2026-08-16T10:00:05",
            "finished_at": "2026-08-16T10:00:15",
            "events": [
                {
                    "id": "event-1",
                    "run_id": "run-complete123456",
                    "message": "Event 1",
                    "created_at": "2026-08-16T10:00:06",
                    "metadata": {},
                }
            ],
            "qualities": [
                {
                    "id": "qual-1",
                    "run_id": "run-complete123456",
                    "kind": "base",
                    "passed": True,
                    "created_at": "2026-08-16T10:00:10",
                    "metrics": {"score": 100},
                }
            ],
        }
        run = BaseRunModel.from_any(data)

        assert run.id == "run-complete123456"
        assert run.bridge_name == "full_bridge"
        assert run.name == "Full Test Run"
        assert run.status == RunStatus.SUCCEEDED
        assert run.created_at.year == 2026
        assert run.started_at.year == 2026
        assert run.finished_at.year == 2026
        assert len(run.events) == 1
        assert len(run.qualities) == 1
        assert run.events[0].message == "Event 1"
        assert run.qualities[0].passed is True

    def test_dataset_with_pending_status(self):
        """Test initialization with pending status dataset."""
        data = {"bridge_name": "pending_bridge", "status": "pending", "name": "Pending Run"}
        run = BaseRunModel.from_any(data)

        assert run.status == RunStatus.PENDING
        assert run.started_at is None
        assert run.finished_at is None

    def test_dataset_with_running_status(self):
        """Test initialization with running status dataset."""
        data = {
            "bridge_name": "running_bridge",
            "status": "running",
            "started_at": "2026-08-16T12:00:00",
        }
        run = BaseRunModel.from_any(data)

        assert run.status == RunStatus.RUNNING
        assert run.started_at is not None
        assert run.finished_at is None

    def test_dataset_with_failed_status(self):
        """Test initialization with failed status dataset."""
        data = {
            "bridge_name": "failed_bridge",
            "status": "failed",
            "started_at": "2026-08-16T12:00:00",
            "finished_at": "2026-08-16T12:00:30",
        }
        run = BaseRunModel.from_any(data)

        assert run.status == RunStatus.FAILED
        assert run.started_at is not None
        assert run.finished_at is not None

    def test_dataset_with_cancelled_status(self):
        """Test initialization with cancelled status dataset."""
        data = {
            "bridge_name": "cancelled_bridge",
            "status": "cancelled",
            "finished_at": "2026-08-16T12:00:30",
        }
        run = BaseRunModel.from_any(data)

        assert run.status == RunStatus.CANCELLED
        assert run.finished_at is not None

    def test_dataset_with_empty_events_list(self):
        """Test initialization with explicit empty events list."""
        data = {"bridge_name": "test_bridge", "events": []}
        run = BaseRunModel.from_any(data)

        assert run.events == []
        assert isinstance(run.events, list)

    def test_dataset_with_empty_qualities_list(self):
        """Test initialization with explicit empty qualities list."""
        data = {"bridge_name": "test_bridge", "qualities": []}
        run = BaseRunModel.from_any(data)

        assert run.qualities == []
        assert isinstance(run.qualities, list)

    def test_dataset_with_multiple_events(self):
        """Test initialization with multiple events."""
        data = {
            "bridge_name": "multi_event_bridge",
            "events": [
                {
                    "id": f"event-{i}",
                    "run_id": "run-test",
                    "message": f"Event {i}",
                    "created_at": "2026-08-16T10:00:00",
                    "metadata": {},
                }
                for i in range(5)
            ],
        }
        run = BaseRunModel.from_any(data)

        assert len(run.events) == 5
        for i, event in enumerate(run.events):
            assert event.message == f"Event {i}"
            assert isinstance(event, BaseEventModel)

    def test_dataset_with_multiple_qualities(self):
        """Test initialization with multiple qualities."""
        data = {
            "bridge_name": "multi_quality_bridge",
            "qualities": [
                {
                    "id": f"qual-{i}",
                    "run_id": "run-test",
                    "kind": "base",
                    "passed": i % 2 == 0,
                    "created_at": "2026-08-16T10:00:00",
                    "metrics": {"iteration": i},
                }
                for i in range(3)
            ],
        }
        run = BaseRunModel.from_any(data)

        assert len(run.qualities) == 3
        for i, quality in enumerate(run.qualities):
            assert quality.passed == (i % 2 == 0)
            assert quality.metrics["iteration"] == i
            assert isinstance(quality, BaseQualityModel)

    def test_dataset_with_datetime_objects(self):
        """Test initialization with datetime objects instead of strings."""
        now = datetime.now()
        data = {
            "bridge_name": "datetime_bridge",
            "created_at": now,
            "started_at": now,
            "finished_at": now,
        }
        run = BaseRunModel.from_any(data)

        assert run.created_at == now
        assert run.started_at == now
        assert run.finished_at == now

    def test_dataset_with_none_created_at_uses_current_time(self):
        """Test that None created_at generates current timestamp."""
        from bastion._internal.clock import IBastionClock

        before = IBastionClock.current()
        data = {"bridge_name": "test_bridge", "created_at": None}
        run = BaseRunModel.from_any(data)
        after = IBastionClock.current()

        assert run.created_at is not None
        assert isinstance(run.created_at, datetime)
        # Verify it's between before and after (with small tolerance)
        assert before <= run.created_at <= after

    def test_dataset_with_none_optional_timestamps(self):
        """Test initialization with None for optional timestamps."""
        data = {"bridge_name": "test_bridge", "started_at": None, "finished_at": None}
        run = BaseRunModel.from_any(data)

        assert run.started_at is None
        assert run.finished_at is None

    def test_dataset_with_iso_format_timestamps(self):
        """Test initialization with ISO format timestamp strings."""
        data = {
            "bridge_name": "iso_bridge",
            "created_at": "2026-08-16T10:00:00.123456",
            "started_at": "2026-08-16T10:00:05.654321",
            "finished_at": "2026-08-16T10:00:15.999999",
        }
        run = BaseRunModel.from_any(data)

        assert run.created_at.microsecond == 123456
        assert run.started_at.microsecond == 654321
        assert run.finished_at.microsecond == 999999

    def test_dataset_missing_optional_fields(self):
        """Test initialization with missing optional fields."""
        data = {"bridge_name": "minimal_bridge"}
        run = BaseRunModel.from_any(data)

        # All optional fields should have defaults
        assert run.name is None
        assert run.status == RunStatus.PENDING
        assert run.started_at is None
        assert run.finished_at is None
        assert run.events == []
        assert run.qualities == []

    def test_dataset_with_custom_name(self):
        """Test initialization with custom run name."""
        data = {"bridge_name": "test_bridge", "name": "Custom Run Name"}
        run = BaseRunModel.from_any(data)

        assert run.name == "Custom Run Name"

    def test_dataset_with_none_name(self):
        """Test initialization with explicit None name."""
        data = {"bridge_name": "test_bridge", "name": None}
        run = BaseRunModel.from_any(data)

        assert run.name is None

    def test_dataset_with_all_status_values(self):
        """Test initialization with each possible status value."""
        statuses = ["pending", "running", "succeeded", "failed", "cancelled"]

        for status in statuses:
            data = {"bridge_name": f"{status}_bridge", "status": status}
            run = BaseRunModel.from_any(data)
            assert run.status.value == status

    def test_dataset_from_export_dict(self):
        """Test initialization from an exported dict structure."""
        # Create a run and export it
        original = BaseRunModel(bridge_name="export_test")
        original.start()
        original.succeed()

        exported = original.export()

        # Initialize new run from exported data
        restored = BaseRunModel.from_any(exported)

        assert restored.id == original.id
        assert restored.bridge_name == original.bridge_name
        assert restored.status == original.status
        assert restored.created_at == original.created_at
        assert restored.started_at == original.started_at
        assert restored.finished_at == original.finished_at

    def test_dataset_with_complex_events_and_qualities(self):
        """Test initialization with complex events and qualities structures."""
        data = {
            "bridge_name": "complex_bridge",
            "status": "succeeded",
            "events": [
                {
                    "id": "event-1",
                    "run_id": "run-complex",
                    "message": "Started processing",
                    "created_at": "2026-08-16T10:00:00",
                    "metadata": {"stage": "init"},
                },
                {
                    "id": "event-2",
                    "run_id": "run-complex",
                    "message": "Processing data",
                    "created_at": "2026-08-16T10:00:05",
                    "metadata": {"stage": "process", "records": 1000},
                },
                {
                    "id": "event-3",
                    "run_id": "run-complex",
                    "message": "Completed",
                    "created_at": "2026-08-16T10:00:10",
                    "metadata": {"stage": "complete", "duration": 10},
                },
            ],
            "qualities": [
                {
                    "id": "qual-1",
                    "run_id": "run-complex",
                    "kind": "base",
                    "passed": True,
                    "created_at": "2026-08-16T10:00:11",
                    "metrics": {
                        "total_records": 1000,
                        "valid_records": 995,
                        "invalid_records": 5,
                        "success_rate": 0.995,
                    },
                }
            ],
        }
        run = BaseRunModel.from_any(data)

        assert run.bridge_name == "complex_bridge"
        assert run.status == RunStatus.SUCCEEDED
        assert len(run.events) == 3
        assert len(run.qualities) == 1
        assert run.events[0].metadata["stage"] == "init"
        assert run.events[1].metadata["records"] == 1000
        assert run.qualities[0].metrics["success_rate"] == 0.995

    def test_dataset_with_string_status_coercion(self):
        """Test that status strings are properly coerced to RunStatus enum."""
        data = {"bridge_name": "coercion_bridge", "status": "running"}
        run = BaseRunModel.from_any(data)

        assert isinstance(run.status, RunStatus)
        assert run.status == RunStatus.RUNNING

    def test_dataset_initialization_maintains_type_safety(self):
        """Test that initialized models maintain proper types."""
        data = {
            "bridge_name": "type_safe_bridge",
            "status": "succeeded",
            "created_at": "2026-08-16T10:00:00",
            "events": [],
            "qualities": [],
        }
        run = BaseRunModel.from_any(data)

        assert isinstance(run.bridge_name, str)
        assert isinstance(run.status, RunStatus)
        assert isinstance(run.created_at, datetime)
        assert isinstance(run.events, list)
        assert isinstance(run.qualities, list)

    def test_multiple_dataset_variations_produce_valid_models(self):
        """Test that various dataset variations all produce valid models."""
        datasets = [
            {"bridge_name": "bridge1"},
            {"bridge_name": "bridge2", "name": "Run 2"},
            {"bridge_name": "bridge3", "status": "running"},
            {"bridge_name": "bridge4", "status": "succeeded", "finished_at": "2026-08-16T10:00:00"},
            {"bridge_name": "bridge5", "events": [], "qualities": []},
        ]

        for data in datasets:
            run = BaseRunModel.from_any(data)
            assert isinstance(run, BaseRunModel)
            assert run.bridge_name == data["bridge_name"]
            assert run.id.startswith("run-")
            assert run.created_at is not None


class TestBaseRunModelRoundtripDataIntegrity:
    """
    Comprehensive roundtrip tests to verify no data loss between
    model creation, export(), and from_any() operations.
    """

    def test_roundtrip_preserves_all_scalar_fields(self):
        """Test that all scalar fields are preserved in roundtrip."""
        original = BaseRunModel(
            bridge_name="test_bridge", name="Test Run Name", status=RunStatus.SUCCEEDED
        )
        original.start()
        original.succeed()

        # Export and recreate
        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        # Verify all fields match exactly
        assert restored.id == original.id
        assert restored.bridge_name == original.bridge_name
        assert restored.name == original.name
        assert restored.status == original.status
        assert restored.created_at == original.created_at
        assert restored.started_at == original.started_at
        assert restored.finished_at == original.finished_at

    def test_roundtrip_preserves_none_values(self):
        """Test that None values are preserved correctly."""
        original = BaseRunModel(bridge_name="test_bridge", name=None)

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        assert restored.name is None
        assert restored.started_at is None
        assert restored.finished_at is None

    def test_roundtrip_all_status_values(self):
        """Test roundtrip preserves all possible status values."""
        statuses = [
            RunStatus.PENDING,
            RunStatus.RUNNING,
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        ]

        for status in statuses:
            original = BaseRunModel(bridge_name="test_bridge", status=status)

            exported = original.export()
            restored = BaseRunModel.from_any(exported)

            assert restored.status == status
            assert isinstance(restored.status, RunStatus)

    def test_roundtrip_preserves_timestamp_precision(self):
        """Test that datetime precision (including microseconds) is preserved."""
        from bastion._internal.clock import IBastionClock

        # Create a run with specific timestamps
        specific_time = IBastionClock.from_iso("2026-08-16T10:15:30.123456")
        original = BaseRunModel(bridge_name="test_bridge", created_at=specific_time)

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        # Verify microsecond precision is maintained
        assert restored.created_at == specific_time
        assert restored.created_at.microsecond == 123456

    def test_roundtrip_preserves_utc_timezone(self):
        """Test that UTC timezone information is preserved in roundtrip."""
        from datetime import UTC

        # Create a run with UTC timezone-aware timestamps
        original = BaseRunModel(bridge_name="test_bridge")
        original.start()
        original.succeed()

        # Verify original has UTC timezone
        assert original.created_at.tzinfo == UTC
        assert original.started_at.tzinfo == UTC
        assert original.finished_at.tzinfo == UTC

        # Export and restore
        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        # Verify timezone is preserved
        assert restored.created_at.tzinfo == UTC
        assert restored.started_at.tzinfo == UTC
        assert restored.finished_at.tzinfo == UTC

        # Verify timezone awareness is maintained
        assert restored.created_at.tzinfo is not None
        assert restored.started_at.tzinfo is not None
        assert restored.finished_at.tzinfo is not None

        # Verify exact datetime equality (including timezone)
        assert restored.created_at == original.created_at
        assert restored.started_at == original.started_at
        assert restored.finished_at == original.finished_at

    def test_roundtrip_preserves_timezone_in_iso_strings(self):
        """Test that timezone is correctly preserved through ISO string format."""
        from datetime import UTC

        # Create run with explicit UTC timestamps
        data = {
            "bridge_name": "test_bridge",
            "created_at": "2026-08-16T10:00:00Z",
            "started_at": "2026-08-16T10:00:05+00:00",
            "finished_at": "2026-08-16T10:00:15.123456Z",
        }

        run = BaseRunModel.from_any(data)

        # Verify all timestamps are UTC timezone-aware
        assert run.created_at.tzinfo == UTC
        assert run.started_at.tzinfo == UTC
        assert run.finished_at.tzinfo == UTC

        # Export and verify ISO format includes timezone
        exported = run.export()
        assert exported["created_at"].endswith("Z") or "+00:00" in exported["created_at"]
        assert exported["started_at"].endswith("Z") or "+00:00" in exported["started_at"]
        assert exported["finished_at"].endswith("Z") or "+00:00" in exported["finished_at"]

        # Restore and verify timezone still preserved
        restored = BaseRunModel.from_any(exported)
        assert restored.created_at.tzinfo == UTC
        assert restored.started_at.tzinfo == UTC
        assert restored.finished_at.tzinfo == UTC

    def test_roundtrip_with_single_event(self):
        """Test roundtrip preserves single event correctly."""
        original = BaseRunModel(bridge_name="test_bridge")
        event = BaseEventModel(
            run_id=original.id, message="Test event", metadata={"key": "value", "count": 42}
        )
        original.events.append(event)

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        assert len(restored.events) == 1
        assert restored.events[0].id == event.id
        assert restored.events[0].run_id == event.run_id
        assert restored.events[0].message == event.message
        assert restored.events[0].metadata == event.metadata

    def test_roundtrip_with_single_quality(self):
        """Test roundtrip preserves single quality correctly."""
        original = BaseRunModel(bridge_name="test_bridge")
        quality = BaseQualityModel(
            run_id=original.id, passed=True, metrics={"accuracy": 0.95, "count": 1000}
        )
        original.qualities.append(quality)

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        assert len(restored.qualities) == 1
        assert restored.qualities[0].id == quality.id
        assert restored.qualities[0].run_id == quality.run_id
        assert restored.qualities[0].passed == quality.passed
        assert restored.qualities[0].metrics == quality.metrics

    def test_roundtrip_with_complex_nested_data(self):
        """Test roundtrip with complex nested events and qualities."""
        original = BaseRunModel(bridge_name="complex_bridge", name="Complex Test")
        original.start()

        # Add multiple events with complex metadata
        for i in range(3):
            event = BaseEventModel(
                run_id=original.id,
                message=f"Event {i}",
                metadata={
                    "stage": f"stage_{i}",
                    "data": {"nested": {"value": i * 10}, "list": [1, 2, 3]},
                    "count": i,
                },
            )
            original.events.append(event)

        # Add multiple qualities with complex metrics
        for i in range(2):
            quality = BaseQualityModel(
                run_id=original.id,
                passed=i % 2 == 0,
                metrics={"score": 0.9 + i * 0.05, "details": {"total": 100 + i, "valid": 95 + i}},
            )
            original.qualities.append(quality)

        original.succeed()

        # Roundtrip
        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        # Verify main fields
        assert restored.id == original.id
        assert restored.bridge_name == original.bridge_name
        assert restored.name == original.name
        assert restored.status == RunStatus.SUCCEEDED

        # Verify events
        assert len(restored.events) == 3
        for i, event in enumerate(restored.events):
            assert event.message == f"Event {i}"
            assert event.metadata["stage"] == f"stage_{i}"
            assert event.metadata["data"]["nested"]["value"] == i * 10
            assert event.metadata["data"]["list"] == [1, 2, 3]
            assert event.metadata["count"] == i

        # Verify qualities
        assert len(restored.qualities) == 2
        for i, quality in enumerate(restored.qualities):
            assert quality.passed == (i % 2 == 0)
            assert quality.metrics["score"] == 0.9 + i * 0.05
            assert quality.metrics["details"]["total"] == 100 + i
            assert quality.metrics["details"]["valid"] == 95 + i

    def test_roundtrip_empty_collections(self):
        """Test that empty events and qualities lists are preserved."""
        original = BaseRunModel(bridge_name="test_bridge")

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        assert restored.events == []
        assert restored.qualities == []
        assert isinstance(restored.events, list)
        assert isinstance(restored.qualities, list)

    def test_roundtrip_with_event_metadata_edge_cases(self):
        """Test roundtrip with various metadata edge cases."""
        original = BaseRunModel(bridge_name="test_bridge")

        # Event with empty metadata
        event1 = BaseEventModel(run_id=original.id, message="Event 1", metadata={})
        original.events.append(event1)

        # Event with None message
        event2 = BaseEventModel(run_id=original.id, message=None, metadata={"key": "val"})
        original.events.append(event2)

        # Event with complex metadata types
        event3 = BaseEventModel(
            run_id=original.id,
            message="Event 3",
            metadata={
                "string": "text",
                "int": 42,
                "float": 3.14,
                "bool": True,
                "null": None,
                "list": [1, "two", 3.0],
                "dict": {"nested": "value"},
            },
        )
        original.events.append(event3)

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        assert len(restored.events) == 3
        assert restored.events[0].metadata == {}
        assert restored.events[1].message is None
        assert restored.events[2].metadata["string"] == "text"
        assert restored.events[2].metadata["int"] == 42
        assert restored.events[2].metadata["float"] == 3.14
        assert restored.events[2].metadata["bool"] is True
        assert restored.events[2].metadata["null"] is None
        assert restored.events[2].metadata["list"] == [1, "two", 3.0]
        assert restored.events[2].metadata["dict"]["nested"] == "value"

    def test_roundtrip_with_quality_metrics_edge_cases(self):
        """Test roundtrip with various quality metrics edge cases."""
        original = BaseRunModel(bridge_name="test_bridge")

        # Quality with empty metrics
        quality1 = BaseQualityModel(run_id=original.id, passed=True, metrics={})
        original.qualities.append(quality1)

        # Quality with various numeric types
        quality2 = BaseQualityModel(
            run_id=original.id,
            passed=False,
            metrics={
                "int_value": 100,
                "float_value": 99.99,
                "zero": 0,
                "negative": -50,
                "very_small": 0.0001,
                "very_large": 1000000,
            },
        )
        original.qualities.append(quality2)

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        assert len(restored.qualities) == 2
        assert restored.qualities[0].metrics == {}
        assert restored.qualities[1].metrics["int_value"] == 100
        assert restored.qualities[1].metrics["float_value"] == 99.99
        assert restored.qualities[1].metrics["zero"] == 0
        assert restored.qualities[1].metrics["negative"] == -50
        assert restored.qualities[1].metrics["very_small"] == 0.0001
        assert restored.qualities[1].metrics["very_large"] == 1000000

    def test_sequential_roundtrips_no_data_degradation(self):
        """Test that sequential roundtrips don't degrade data."""
        original = BaseRunModel(bridge_name="test_bridge", name="Roundtrip Test")
        original.start()

        event = BaseEventModel(
            run_id=original.id, message="Test", metadata={"value": 123, "nested": {"key": "data"}}
        )
        original.events.append(event)

        quality = BaseQualityModel(run_id=original.id, passed=True, metrics={"score": 0.95})
        original.qualities.append(quality)

        original.succeed()

        # Perform 5 sequential roundtrips
        current = original
        for i in range(5):
            exported = current.export()
            current = BaseRunModel.from_any(exported)

        # After 5 roundtrips, data should be identical
        assert current.id == original.id
        assert current.bridge_name == original.bridge_name
        assert current.name == original.name
        assert current.status == original.status
        assert current.created_at == original.created_at
        assert current.started_at == original.started_at
        assert current.finished_at == original.finished_at

        assert len(current.events) == 1
        assert current.events[0].message == "Test"
        assert current.events[0].metadata == {"value": 123, "nested": {"key": "data"}}

        assert len(current.qualities) == 1
        assert current.qualities[0].passed is True
        assert current.qualities[0].metrics == {"score": 0.95}

    def test_roundtrip_after_state_transitions(self):
        """Test roundtrip after various state transitions."""
        # Test PENDING -> RUNNING -> SUCCEEDED
        run1 = BaseRunModel(bridge_name="bridge1")
        assert run1.status == RunStatus.PENDING

        run1.start()
        exported1 = run1.export()
        restored1 = BaseRunModel.from_any(exported1)
        assert restored1.status == RunStatus.RUNNING
        assert restored1.started_at == run1.started_at

        run1.succeed()
        exported2 = run1.export()
        restored2 = BaseRunModel.from_any(exported2)
        assert restored2.status == RunStatus.SUCCEEDED
        assert restored2.finished_at == run1.finished_at

        # Test PENDING -> RUNNING -> FAILED
        run2 = BaseRunModel(bridge_name="bridge2")
        run2.start()
        run2.fail()

        exported3 = run2.export()
        restored3 = BaseRunModel.from_any(exported3)
        assert restored3.status == RunStatus.FAILED
        assert restored3.started_at is not None
        assert restored3.finished_at is not None

        # Test PENDING -> CANCELLED
        run3 = BaseRunModel(bridge_name="bridge3")
        run3.cancel()

        exported4 = run3.export()
        restored4 = BaseRunModel.from_any(exported4)
        assert restored4.status == RunStatus.CANCELLED
        assert restored4.started_at is None
        assert restored4.finished_at is not None

    def test_roundtrip_preserves_event_order(self):
        """Test that event order is preserved in roundtrip."""
        original = BaseRunModel(bridge_name="test_bridge")

        # Add events with specific order
        messages = ["First", "Second", "Third", "Fourth", "Fifth"]
        for msg in messages:
            event = BaseEventModel(run_id=original.id, message=msg)
            original.events.append(event)

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        # Verify order is preserved
        assert len(restored.events) == 5
        for i, msg in enumerate(messages):
            assert restored.events[i].message == msg

    def test_roundtrip_preserves_quality_order(self):
        """Test that quality order is preserved in roundtrip."""
        original = BaseRunModel(bridge_name="test_bridge")

        # Add qualities with specific order and scores
        scores = [0.1, 0.3, 0.5, 0.7, 0.9]
        for score in scores:
            quality = BaseQualityModel(
                run_id=original.id, passed=score > 0.5, metrics={"score": score}
            )
            original.qualities.append(quality)

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        # Verify order is preserved
        assert len(restored.qualities) == 5
        for i, score in enumerate(scores):
            assert restored.qualities[i].metrics["score"] == score

    def test_roundtrip_with_unicode_and_special_characters(self):
        """Test roundtrip preserves unicode and special characters."""
        original = BaseRunModel(bridge_name="test_bridge", name="测试运行 🚀 Test™")

        event = BaseEventModel(
            run_id=original.id,
            message="Unicode: 你好世界 emoji: 😀🎉 symbols: ©®™",
            metadata={"unicode_key": "值", "special": "tab\ttab newline\n quote'\" backslash\\"},
        )
        original.events.append(event)

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        assert restored.name == "测试运行 🚀 Test™"
        assert restored.events[0].message == "Unicode: 你好世界 emoji: 😀🎉 symbols: ©®™"
        assert restored.events[0].metadata["unicode_key"] == "值"
        assert restored.events[0].metadata["special"] == "tab\ttab newline\n quote'\" backslash\\"

    def test_roundtrip_with_large_collections(self):
        """Test roundtrip with large numbers of events and qualities."""
        original = BaseRunModel(bridge_name="test_bridge")

        # Add 100 events
        for i in range(100):
            event = BaseEventModel(
                run_id=original.id, message=f"Event {i}", metadata={"index": i, "square": i * i}
            )
            original.events.append(event)

        # Add 50 qualities
        for i in range(50):
            quality = BaseQualityModel(
                run_id=original.id, passed=i % 3 == 0, metrics={"index": i, "value": i * 0.01}
            )
            original.qualities.append(quality)

        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        # Verify counts
        assert len(restored.events) == 100
        assert len(restored.qualities) == 50

        # Spot check some values
        assert restored.events[0].message == "Event 0"
        assert restored.events[99].message == "Event 99"
        assert restored.events[50].metadata["square"] == 2500

        assert restored.qualities[0].passed is True
        assert restored.qualities[49].metrics["value"] == 0.49
        assert restored.qualities[10].passed is False

    def test_roundtrip_comparison_with_direct_init(self):
        """Test that from_any(export()) produces same result as direct init."""
        # Create via direct initialization
        direct = BaseRunModel(bridge_name="test_bridge", name="Test Run")

        # Create via export -> from_any
        exported = direct.export()
        from_export = BaseRunModel.from_any(exported)

        # Both should be functionally equivalent
        assert from_export.bridge_name == direct.bridge_name
        assert from_export.name == direct.name
        assert from_export.status == direct.status
        # Note: IDs may differ if generated, but other fields should match

    def test_roundtrip_no_data_loss_assertion(self):
        """Comprehensive test asserting zero data loss in roundtrip."""
        original = BaseRunModel(bridge_name="comprehensive_test", name="Data Integrity Test")
        original.start()

        # Add diverse data
        event1 = BaseEventModel(
            run_id=original.id,
            message="Event with metadata",
            metadata={"key1": "value1", "key2": 42, "key3": [1, 2, 3]},
        )
        event2 = BaseEventModel(run_id=original.id, message=None, metadata={})
        original.events.extend([event1, event2])

        quality1 = BaseQualityModel(
            run_id=original.id, passed=True, metrics={"accuracy": 0.95, "precision": 0.92}
        )
        original.qualities.append(quality1)

        original.succeed()

        # Perform roundtrip
        exported = original.export()
        restored = BaseRunModel.from_any(exported)

        # Re-export restored
        re_exported = restored.export()

        # The two exported dicts should be identical
        assert exported == re_exported, "Data loss detected: exported dicts differ"
