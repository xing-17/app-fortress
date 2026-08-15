from __future__ import annotations

import pytest

from bastion.domain.run.base import RunStatus
from bastion.metadata.event import Event
from bastion.metadata.quality import Quality
from bastion.metadata.run import Run


class TestRun:
    """Test suite for Run class."""

    def test_run_initialization(self):
        """Test basic run initialization."""
        run = Run(bridge_name="test_bridge")
        assert run.domain.bridge_name == "test_bridge"
        assert run.id is not None
        assert run.status == RunStatus.PENDING
        assert len(run.events) == 0
        assert len(run.qualities) == 0

    def test_run_with_status(self):
        """Test run initialization with specific status."""
        run = Run(bridge_name="test_bridge", status=RunStatus.RUNNING)
        assert run.status == RunStatus.RUNNING

    def test_run_from_dict(self):
        """Test creating run from dictionary."""
        data = {
            "bridge_name": "test_bridge",
            "status": "running",
            "events": [],
            "qualities": [],
        }
        run = Run.from_any(data)
        assert run.domain.bridge_name == "test_bridge"
        assert run.status == RunStatus.RUNNING

    def test_run_from_dict_with_events(self):
        """Test creating run from dictionary with events."""
        data = {
            "bridge_name": "test_bridge",
            "events": [
                {"run_id": "run-123", "message": "Event 1"},
                {"run_id": "run-123", "message": "Event 2"},
            ],
            "qualities": [],
        }
        run = Run.from_any(data)
        assert len(run.events) == 2
        assert run.events[0].domain.message == "Event 1"
        assert run.events[1].domain.message == "Event 2"

    def test_run_from_dict_with_qualities(self):
        """Test creating run from dictionary with qualities."""
        data = {
            "bridge_name": "test_bridge",
            "events": [],
            "qualities": [
                {"run_id": "run-123", "passed": True},
                {"run_id": "run-123", "passed": False},
            ],
        }
        run = Run.from_any(data)
        assert len(run.qualities) == 2
        assert run.qualities[0].domain.passed is True
        assert run.qualities[1].domain.passed is False

    def test_run_from_run(self):
        """Test creating run from another run instance."""
        run1 = Run(bridge_name="test_bridge")
        run2 = Run.from_any(run1)
        assert run1.id == run2.id
        assert run1.domain.bridge_name == run2.domain.bridge_name

    def test_run_add_event(self):
        """Test adding event to run."""
        run = Run(bridge_name="test_bridge")
        event = Event(run_id=run.id, message="Test event")
        run.add_event(event)
        assert len(run.events) == 1
        assert run.events[0].domain.message == "Test event"

    def test_run_add_duplicate_event(self):
        """Test adding duplicate event to run."""
        run = Run(bridge_name="test_bridge")
        event = Event(run_id=run.id, message="Test event")
        run.add_event(event)
        run.add_event(event)  # Should be ignored
        assert len(run.events) == 1

    def test_run_add_quality(self):
        """Test adding quality to run."""
        run = Run(bridge_name="test_bridge")
        quality = Quality(run_id=run.id, passed=True)
        run.add_quality(quality)
        assert len(run.qualities) == 1
        assert run.qualities[0].domain.passed is True

    def test_run_add_duplicate_quality(self):
        """Test adding duplicate quality to run."""
        run = Run(bridge_name="test_bridge")
        quality = Quality(run_id=run.id, passed=True)
        run.add_quality(quality)
        run.add_quality(quality)  # Should be ignored
        assert len(run.qualities) == 1

    def test_run_start(self):
        """Test starting a run."""
        run = Run(bridge_name="test_bridge")
        assert run.status == RunStatus.PENDING
        run.start()
        assert run.status == RunStatus.RUNNING
        assert run.domain.started_at is not None

    def test_run_succeed(self):
        """Test marking run as succeeded."""
        run = Run(bridge_name="test_bridge")
        run.start()
        run.succeed()
        assert run.status == RunStatus.SUCCEEDED
        assert run.domain.finished_at is not None

    def test_run_fail(self):
        """Test marking run as failed."""
        run = Run(bridge_name="test_bridge")
        run.start()
        run.fail()
        assert run.status == RunStatus.FAILED
        assert run.domain.finished_at is not None

    def test_run_cancel(self):
        """Test cancelling a run."""
        run = Run(bridge_name="test_bridge")
        run.start()
        run.cancel()
        assert run.status == RunStatus.CANCELLED
        assert run.domain.finished_at is not None

    def test_run_export(self):
        """Test run export to dictionary."""
        run = Run(bridge_name="test_bridge")
        event = Event(run_id=run.id, message="Test event")
        quality = Quality(run_id=run.id, passed=True)
        run.add_event(event)
        run.add_quality(quality)

        exported = run.export()
        assert exported["bridge_name"] == "test_bridge"
        assert exported["status"] == "pending"
        assert len(exported["events"]) == 1
        assert len(exported["qualities"]) == 1
        assert "id" in exported
        assert "created_at" in exported

    def test_run_sha256_key(self):
        """Test run SHA256 key generation."""
        run = Run(bridge_name="test_bridge")
        sha_key = run._sha256_key
        assert isinstance(sha_key, str)
        assert len(sha_key) > 0

    def test_run_from_invalid_data(self):
        """Test run creation with invalid data."""
        with pytest.raises(ValueError):
            Run.from_any({"invalid": "data"})
