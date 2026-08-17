"""
Unit tests for bastion.control.run.run module.
"""

from datetime import datetime

import pytest

from bastion.control.run.event import Event
from bastion.control.run.quality import Quality
from bastion.control.run.run import IRunLike, Run, RunModel, RunStatus


class TestRun:
    """Test Run class."""

    def test_create_run_minimal(self):
        """Test creating a basic run."""
        run = Run(bridge_name="test_bridge")
        assert run.bridge_name == "test_bridge"
        assert run.name is None
        assert run.status == RunStatus.PENDING
        assert isinstance(run.created_at, datetime)
        assert run.started_at is None
        assert run.finished_at is None
        assert run.id != ""
        assert run.id.startswith("run-")
        assert run.events == []
        assert run.qualities == []

    def test_create_run_with_name(self):
        """Test creating run with name."""
        run = Run(
            bridge_name="test_bridge",
            name="my_run",
        )
        assert run.bridge_name == "test_bridge"
        assert run.name == "my_run"

    def test_create_run_with_custom_id(self):
        """Test creating run with custom ID."""
        custom_id = "run-custom12345678"
        run = Run(
            bridge_name="test_bridge",
            id=custom_id,
        )
        assert run.id == custom_id

    def test_create_run_with_status(self):
        """Test creating run with initial status."""
        run = Run(
            bridge_name="test_bridge",
            status=RunStatus.RUNNING,
        )
        assert run.status == RunStatus.RUNNING

    def test_create_run_with_status_string(self):
        """Test creating run with status as string."""
        run = Run(
            bridge_name="test_bridge",
            status="running",
        )
        assert run.status == RunStatus.RUNNING

    def test_create_run_with_timestamps(self):
        """Test creating run with custom timestamps."""
        created = datetime(2026, 8, 14, 10, 0, 0)
        started = datetime(2026, 8, 14, 10, 0, 1)
        run = Run(
            bridge_name="test_bridge",
            created_at=created,
            started_at=started,
        )
        assert run.created_at == created
        assert run.started_at == started

    def test_create_run_with_events_and_qualities(self):
        """Test creating run with initial events and qualities."""
        # Create run first, then add events and qualities
        run = Run(bridge_name="test_bridge")
        event = Event(run_id=run.id, message="Init event")
        quality = Quality(run_id=run.id, kind="init", passed=True)

        run.add_event(event)
        run.add_quality(quality)

        assert len(run.events) == 1
        assert len(run.qualities) == 1

    def test_missing_bridge_name_raises(self):
        """Test creating run without bridge_name raises error."""
        with pytest.raises(TypeError):
            Run()

    def test_id_generation(self):
        """Test that runs have unique IDs with correct prefix."""
        run1 = Run(bridge_name="bridge1")
        run2 = Run(bridge_name="bridge2")

        assert run1.id != run2.id
        assert run1.id.startswith("run-")
        assert run2.id.startswith("run-")
        assert len(run1.id.split("-")[1]) == 16


class TestRunStateTransitions:
    """Test Run state transition methods."""

    def test_start_method(self):
        """Test start() sets status to RUNNING and started_at."""
        run = Run(bridge_name="test_bridge")
        assert run.status == RunStatus.PENDING
        assert run.started_at is None

        run.start()

        assert run.status == RunStatus.RUNNING
        assert run.started_at is not None
        assert isinstance(run.started_at, datetime)

    def test_succeed_method(self):
        """Test succeed() sets status to SUCCEEDED and finished_at."""
        run = Run(bridge_name="test_bridge")
        run.start()
        assert run.finished_at is None

        run.succeed()

        assert run.status == RunStatus.SUCCEEDED
        assert run.finished_at is not None
        assert isinstance(run.finished_at, datetime)

    def test_fail_method(self):
        """Test fail() sets status to FAILED and finished_at."""
        run = Run(bridge_name="test_bridge")
        run.start()

        run.fail()

        assert run.status == RunStatus.FAILED
        assert run.finished_at is not None
        assert isinstance(run.finished_at, datetime)

    def test_cancel_method(self):
        """Test cancel() sets status to CANCELLED and finished_at."""
        run = Run(bridge_name="test_bridge")

        run.cancel()

        assert run.status == RunStatus.CANCELLED
        assert run.finished_at is not None
        assert isinstance(run.finished_at, datetime)

    def test_full_success_workflow(self):
        """Test complete success workflow."""
        run = Run(bridge_name="test_bridge")
        assert run.status == RunStatus.PENDING
        assert run.started_at is None
        assert run.finished_at is None

        run.start()
        assert run.status == RunStatus.RUNNING
        assert run.started_at is not None
        assert run.finished_at is None

        run.succeed()
        assert run.status == RunStatus.SUCCEEDED
        assert run.finished_at is not None

    def test_full_failure_workflow(self):
        """Test complete failure workflow."""
        run = Run(bridge_name="test_bridge")
        assert run.status == RunStatus.PENDING

        run.start()
        assert run.status == RunStatus.RUNNING

        run.fail()
        assert run.status == RunStatus.FAILED
        assert run.finished_at is not None


class TestRunEventManagement:
    """Test Run event management methods."""

    def test_list_events_empty(self):
        """Test list_events returns empty list initially."""
        run = Run(bridge_name="test_bridge")
        events = run.list_events()
        assert events == []
        assert isinstance(events, list)

    def test_event_method(self):
        """Test event() creates and adds event."""
        run = Run(bridge_name="test_bridge")
        run.event(message="Test event")

        events = run.list_events()
        assert len(events) == 1
        assert events[0].message == "Test event"
        assert events[0].run_id == run.id

    def test_event_method_with_metadata(self):
        """Test event() with metadata."""
        run = Run(bridge_name="test_bridge")
        metadata = {"key": "value", "count": 42}
        run.event(message="Event with metadata", metadata=metadata)

        events = run.list_events()
        assert len(events) == 1
        assert events[0].metadata == metadata

    def test_add_event_method(self):
        """Test add_event() adds event to run."""
        run = Run(bridge_name="test_bridge")
        event = Event(run_id=run.id, message="Manual event")

        run.add_event(event)

        events = run.list_events()
        assert len(events) == 1
        assert events[0].message == "Manual event"

    def test_add_event_prevents_duplicates(self):
        """Test add_event() prevents duplicate events based on sha256."""
        run = Run(bridge_name="test_bridge")
        event = Event(
            run_id=run.id,
            id="event-test123456789",
            message="Duplicate test",
        )

        run.add_event(event)
        run.add_event(event)  # Try to add same event again

        events = run.list_events()
        assert len(events) == 1  # Should only have one

    def test_multiple_events(self):
        """Test adding multiple different events."""
        run = Run(bridge_name="test_bridge")
        run.event(message="Event 1")
        run.event(message="Event 2")
        run.event(message="Event 3")

        events = run.list_events()
        assert len(events) == 3
        assert events[0].message == "Event 1"
        assert events[1].message == "Event 2"
        assert events[2].message == "Event 3"


class TestRunQualityManagement:
    """Test Run quality management methods."""

    def test_list_qualities_empty(self):
        """Test list_qualities returns empty list initially."""
        run = Run(bridge_name="test_bridge")
        qualities = run.list_qualities()
        assert qualities == []
        assert isinstance(qualities, list)

    def test_quality_method(self):
        """Test quality() creates and adds quality check."""
        run = Run(bridge_name="test_bridge")
        run.quality(
            kind="validation",
            passed=True,
            description="Test quality",
        )

        qualities = run.list_qualities()
        assert len(qualities) == 1
        assert qualities[0].kind == "validation"
        assert qualities[0].passed is True
        assert qualities[0].description == "Test quality"
        assert qualities[0].run_id == run.id

    def test_quality_method_with_metrics(self):
        """Test quality() with metrics."""
        run = Run(bridge_name="test_bridge")
        metrics = {"accuracy": 0.95, "precision": 0.92}
        run.quality(
            kind="ml_validation",
            passed=True,
            metrics=metrics,
        )

        qualities = run.list_qualities()
        assert len(qualities) == 1
        assert qualities[0].metrics == metrics

    def test_quality_method_with_minimal_params(self):
        """Test quality() with minimal parameters."""
        run = Run(bridge_name="test_bridge")
        run.quality()

        qualities = run.list_qualities()
        assert len(qualities) == 1
        assert qualities[0].kind is not None  # Should have default

    def test_add_quality_method(self):
        """Test add_quality() adds quality to run."""
        run = Run(bridge_name="test_bridge")
        quality = Quality(
            run_id=run.id,
            kind="manual",
            passed=False,
        )

        run.add_quality(quality)

        qualities = run.list_qualities()
        assert len(qualities) == 1
        assert qualities[0].kind == "manual"
        assert qualities[0].passed is False

    def test_add_quality_prevents_duplicates(self):
        """Test add_quality() prevents duplicate qualities based on sha256."""
        run = Run(bridge_name="test_bridge")
        quality = Quality(
            run_id=run.id,
            id="qual-test123456789012",
            kind="duplicate_test",
            passed=True,
        )

        run.add_quality(quality)
        run.add_quality(quality)  # Try to add same quality again

        qualities = run.list_qualities()
        assert len(qualities) == 1  # Should only have one

    def test_multiple_qualities(self):
        """Test adding multiple different qualities."""
        run = Run(bridge_name="test_bridge")
        run.quality(kind="check1", passed=True)
        run.quality(kind="check2", passed=True)
        run.quality(kind="check3", passed=False)

        qualities = run.list_qualities()
        assert len(qualities) == 3
        assert qualities[0].kind == "check1"
        assert qualities[1].kind == "check2"
        assert qualities[2].kind == "check3"


class TestRunSerialization:
    """Test Run serialization and deserialization."""

    def test_export(self):
        """Test export method returns correct dictionary."""
        run = Run(
            bridge_name="test_bridge",
            name="export_test",
        )
        exported = run.export()

        assert isinstance(exported, dict)
        assert exported["id"] == run.id
        assert exported["bridge_name"] == "test_bridge"
        assert exported["name"] == "export_test"
        assert exported["status"] == "pending"
        assert isinstance(exported["created_at"], str)
        assert exported["started_at"] is None
        assert exported["finished_at"] is None
        assert exported["events"] == []
        assert exported["qualities"] == []

    def test_export_with_timestamps(self):
        """Test export includes timestamps after state transitions."""
        run = Run(bridge_name="test_bridge")
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

    def test_export_with_events_and_qualities(self):
        """Test export includes events and qualities."""
        run = Run(bridge_name="test_bridge")
        run.event(message="Test event")
        run.quality(kind="test", passed=True)
        exported = run.export()

        assert len(exported["events"]) == 1
        assert len(exported["qualities"]) == 1
        assert exported["events"][0]["message"] == "Test event"
        assert exported["qualities"][0]["kind"] == "test"

    def test_from_dict(self):
        """Test from_dict creates Run from dictionary."""
        data = {
            "id": "run-abc123def456",
            "bridge_name": "test_bridge",
            "name": "dict_test",
            "status": "running",
            "created_at": "2026-08-14T10:00:00",
            "started_at": "2026-08-14T10:00:01",
            "finished_at": None,
        }
        run = Run.from_dict(data)
        assert run.id == "run-abc123def456"
        assert run.bridge_name == "test_bridge"
        assert run.name == "dict_test"
        assert run.status == RunStatus.RUNNING

    def test_from_domain(self):
        """Test from_domain creates Run from domain model."""
        domain = RunModel(
            bridge_name="test_bridge",
            name="domain_test",
        )
        run = Run.from_domain(domain)
        assert run.bridge_name == "test_bridge"
        assert run.name == "domain_test"
        assert run.status == RunStatus.PENDING

    def test_roundtrip_export_from_dict(self, run_basic):
        """Test export and from_dict roundtrip conversion."""
        original = run_basic
        original.start()
        original.event(message="Roundtrip event")
        original.quality(kind="roundtrip", passed=True)
        original.succeed()

        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = Run.from_dict(exported)

        # Verify all fields match
        assert restored.id == original.id
        assert restored.bridge_name == original.bridge_name
        assert restored.name == original.name
        assert restored.status == original.status
        assert restored.created_at == original.created_at
        assert restored.started_at == original.started_at
        assert restored.finished_at == original.finished_at
        assert len(restored.events) == len(original.events)
        assert len(restored.qualities) == len(original.qualities)

    def test_describe_returns_json_string(self):
        """Test describe method returns formatted JSON string."""
        run = Run(
            bridge_name="test_bridge",
            name="describe_test",
        )
        description = run.describe()
        assert isinstance(description, str)
        # Should be valid JSON
        import json

        parsed = json.loads(description)
        assert parsed["bridge_name"] == "test_bridge"
        assert parsed["name"] == "describe_test"


class TestRunProtocol:
    """Test Run protocol compliance and domain access."""

    def test_protocol_compliance(self):
        """Test Run implements IRunLike protocol."""
        run = Run(bridge_name="test_bridge")
        assert isinstance(run, IRunLike)

    def test_domain_attribute_access(self):
        """Test accessing domain attributes through wrapper."""
        run = Run(
            bridge_name="test_bridge",
            name="access_test",
        )
        # Access domain directly
        assert run.domain is not None
        assert isinstance(run.domain, RunModel)
        # Access via wrapper
        assert run.id == run.domain.id
        assert run.bridge_name == run.domain.bridge_name

    def test_sha256_property(self):
        """Test sha256 property exists and is consistent."""
        run = Run(bridge_name="test_bridge")
        sha1 = run.sha256
        sha2 = run.sha256
        assert sha1 == sha2
        assert isinstance(sha1, str)
        assert len(sha1) > 0

    def test_logic_name_property(self):
        """Test logic_name property exists."""
        run = Run(
            bridge_name="test_bridge",
            name="logic_test",
        )
        logic_name = run.logic_name
        assert logic_name is not None


class TestRunHooks:
    """Test Run hook methods for extensibility."""

    def test_on_start_hook_called(self):
        """Test _on_start() is called during start()."""

        class CustomRun(Run):
            hook_called = False

            def _on_start(self):
                CustomRun.hook_called = True

        run = CustomRun(bridge_name="test_bridge")
        run.start()

        assert CustomRun.hook_called is True

    def test_on_succeed_hook_called(self):
        """Test _on_succeed() is called during succeed()."""

        class CustomRun(Run):
            hook_called = False

            def _on_succeed(self):
                CustomRun.hook_called = True

        run = CustomRun(bridge_name="test_bridge")
        run.succeed()

        assert CustomRun.hook_called is True

    def test_on_fail_hook_called(self):
        """Test _on_fail() is called during fail()."""

        class CustomRun(Run):
            hook_called = False

            def _on_fail(self):
                CustomRun.hook_called = True

        run = CustomRun(bridge_name="test_bridge")
        run.fail()

        assert CustomRun.hook_called is True

    def test_on_cancel_hook_called(self):
        """Test _on_cancel() is called during cancel()."""

        class CustomRun(Run):
            hook_called = False

            def _on_cancel(self):
                CustomRun.hook_called = True

        run = CustomRun(bridge_name="test_bridge")
        run.cancel()

        assert CustomRun.hook_called is True
