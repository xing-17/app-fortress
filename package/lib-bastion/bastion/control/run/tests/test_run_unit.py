"""Unit tests for run control."""

from __future__ import annotations

from datetime import datetime

from bastion.control.run.event import Event
from bastion.control.run.run import IRunLike, Run
from bastion.domain.run import RunModel
from bastion.domain.runstatus import RunStatus


class TestIRunLikeProtocol:
    """Test IRunLike protocol definition."""

    def test_protocol_check_with_run(self):
        """Test that Run implements IRunLike protocol."""
        run = Run.from_dict(
            {
                "compute_name": "test_compute",
                "name": "test_run",
            }
        )

        assert isinstance(run, IRunLike)

    def test_protocol_required_attributes(self):
        """Test protocol required attributes are accessible."""
        run = Run.from_dict(
            {
                "compute_name": "test_compute",
                "name": "test_run",
                "status": "pending",
            }
        )

        # Test protocol attributes
        assert run.compute_name == "test_compute"
        assert run.name == "test_run"
        assert run.status == RunStatus.PENDING
        assert hasattr(run, "id")
        assert hasattr(run, "created_at")
        assert run.started_at is None
        assert run.finished_at is None

    def test_protocol_required_methods(self):
        """Test protocol required methods exist."""
        run = Run(compute_name="test_compute")

        # Test protocol methods
        assert hasattr(run, "start")
        assert hasattr(run, "succeed")
        assert hasattr(run, "fail")
        assert hasattr(run, "cancel")
        assert hasattr(run, "event")
        assert hasattr(run, "list_events")
        assert hasattr(run, "export")
        assert hasattr(run, "describe")


class TestRunCreation:
    """Test Run creation and initialization."""

    def test_create_from_kwargs(self):
        """Test creating run with keyword arguments."""
        run = Run(compute_name="test_compute", name="test_run")

        assert run.compute_name == "test_compute"
        assert run.name == "test_run"
        assert run.status == RunStatus.PENDING
        assert run.id.startswith("run-")
        assert isinstance(run.created_at, datetime)

    def test_create_from_dict(self):
        """Test creating run from dictionary."""
        data = {
            "compute_name": "test_compute",
            "name": "test_run",
            "status": "pending",
        }

        run = Run.from_dict(data)

        assert run.compute_name == "test_compute"
        assert run.name == "test_run"
        assert run.status == RunStatus.PENDING

    def test_create_from_domain(self):
        """Test creating run from domain model."""
        domain = RunModel(
            compute_name="test_compute",
            name="test_run",
        )

        run = Run.from_domain(domain)

        assert run.compute_name == "test_compute"
        assert run.name == "test_run"
        assert isinstance(run.domain, RunModel)


class TestRunStatusTransitions:
    """Test run status transition methods."""

    def test_start_transitions_to_running(self):
        """Test start() sets status to RUNNING and records timestamp."""
        run = Run(compute_name="test_compute")

        assert run.status == RunStatus.PENDING
        assert run.started_at is None

        run.start()

        assert run.status == RunStatus.RUNNING
        assert run.started_at is not None
        assert isinstance(run.started_at, datetime)

    def test_succeed_transitions_to_succeeded(self):
        """Test succeed() sets status to SUCCEEDED and records timestamp."""
        run = Run(compute_name="test_compute")
        run.start()

        assert run.finished_at is None

        run.succeed()

        assert run.status == RunStatus.SUCCEEDED
        assert run.finished_at is not None
        assert isinstance(run.finished_at, datetime)

    def test_fail_transitions_to_failed(self):
        """Test fail() sets status to FAILED and records timestamp."""
        run = Run(compute_name="test_compute")
        run.start()

        assert run.finished_at is None

        run.fail()

        assert run.status == RunStatus.FAILED
        assert run.finished_at is not None
        assert isinstance(run.finished_at, datetime)

    def test_cancel_transitions_to_cancelled(self):
        """Test cancel() sets status to CANCELLED and records timestamp."""
        run = Run(compute_name="test_compute")

        assert run.finished_at is None

        run.cancel()

        assert run.status == RunStatus.CANCELLED
        assert run.finished_at is not None
        assert isinstance(run.finished_at, datetime)


class TestRunEventManagement:
    """Test run event creation and management."""

    def test_create_event_adds_to_run(self):
        """Test event() creates and adds event to run."""
        run = Run(compute_name="test_compute")

        assert len(run.events) == 0

        run.event("Test message")

        assert len(run.events) == 1
        assert run.events[0].message == "Test message"
        assert run.events[0].run_id == run.id

    def test_create_event_with_metadata(self):
        """Test event() with metadata."""
        run = Run(compute_name="test_compute")

        metadata = {"key": "value", "count": 42}
        run.event("Test message", metadata=metadata)

        assert len(run.events) == 1
        assert run.events[0].metadata == metadata

    def test_add_event_directly(self):
        """Test add_event() adds existing event."""
        run = Run(compute_name="test_compute")
        event = Event(run_id=run.id, message="Direct event")

        run.add_event(event)

        assert len(run.events) == 1
        assert run.events[0].message == "Direct event"

    def test_list_events_returns_all_events(self):
        """Test list_events() returns all events."""
        run = Run(compute_name="test_compute")

        run.event("Event 1")
        run.event("Event 2")
        run.event("Event 3")

        events = run.list_events()

        assert len(events) == 3
        assert events[0].message == "Event 1"
        assert events[1].message == "Event 2"
        assert events[2].message == "Event 3"


class TestRunSerialization:
    """Test run export and serialization."""

    def test_export_returns_dict(self):
        """Test export() returns dictionary."""
        run = Run(compute_name="test_compute", name="test_run")
        run.start()
        run.event("Test event")

        exported = run.export()

        assert isinstance(exported, dict)
        assert exported["compute_name"] == "test_compute"
        assert exported["name"] == "test_run"
        assert exported["status"] == "running"
        assert "id" in exported
        assert "created_at" in exported
        assert "started_at" in exported

    def test_describe_returns_string(self):
        """Test describe() returns JSON string."""
        run = Run(compute_name="test_compute")

        described = run.describe()

        assert isinstance(described, str)
        assert "test_compute" in described
