"""Unit tests for event control."""

from __future__ import annotations

from datetime import datetime

from bastion.control.run.event import Event
from bastion.domain.event import EventModel


class TestIEventLikeProtocol:
    """Test IEventLike protocol definition."""

    def test_protocol_required_attributes_exist(self):
        """Test that Event has required protocol attributes."""
        event = Event(
            run_id="run-test123",
            message="Test event",
        )

        # Verify all protocol attributes exist
        assert hasattr(event, "id")
        assert hasattr(event, "run_id")
        assert hasattr(event, "message")
        assert hasattr(event, "metadata")
        assert hasattr(event, "created_at")
        assert hasattr(event, "tags")

    def test_protocol_required_attributes(self):
        """Test protocol required attributes are accessible."""
        metadata = {"key": "value"}
        tags = {"severity": "info"}

        event = Event(
            run_id="run-test123",
            message="Test event",
            metadata=metadata,
            tags=tags,
        )

        # Test protocol attributes
        assert event.run_id == "run-test123"
        assert event.message == "Test event"
        assert event.metadata == metadata
        assert event.tags == tags
        assert hasattr(event, "id")
        assert hasattr(event, "created_at")

    def test_protocol_required_methods(self):
        """Test protocol required methods exist."""
        event = Event(run_id="run-test123", message="Test")

        # Test protocol methods
        assert hasattr(event, "export")
        assert hasattr(event, "describe")
        assert callable(event.export)
        assert callable(event.describe)


class TestEventCreation:
    """Test Event creation and initialization."""

    def test_create_with_minimal_args(self):
        """Test creating event with minimal required arguments."""
        event = Event(run_id="run-test123", message="Test message")

        assert event.run_id == "run-test123"
        assert event.message == "Test message"
        assert event.id.startswith("event-")
        assert isinstance(event.created_at, datetime)

    def test_create_with_metadata(self):
        """Test creating event with metadata."""
        metadata = {"key": "value", "count": 42}
        event = Event(
            run_id="run-test123",
            message="Test message",
            metadata=metadata,
        )

        assert event.metadata == metadata

    def test_create_with_tags(self):
        """Test creating event with tags."""
        tags = {"severity": "error", "component": "processor"}
        event = Event(
            run_id="run-test123",
            message="Test message",
            tags=tags,
        )

        assert event.tags == tags

    def test_create_from_dict(self):
        """Test creating event from dictionary."""
        data = {
            "run_id": "run-test123",
            "message": "Test message",
            "metadata": {"key": "value"},
        }

        event = Event.from_dict(data)

        assert event.run_id == "run-test123"
        assert event.message == "Test message"
        assert event.metadata == {"key": "value"}


class TestEventAlias:
    """Test that Event is an alias for EventModel."""

    def test_event_is_eventmodel(self):
        """Test Event is the same as EventModel."""
        assert Event is EventModel

    def test_event_instance_is_eventmodel_instance(self):
        """Test Event instance is EventModel instance."""
        event = Event(run_id="run-test123", message="Test")

        assert isinstance(event, EventModel)
        assert isinstance(event, Event)


class TestEventSerialization:
    """Test event export and serialization."""

    def test_export_returns_dict(self):
        """Test export() returns dictionary."""
        event = Event(
            run_id="run-test123",
            message="Test message",
            metadata={"key": "value"},
        )

        exported = event.export()

        assert isinstance(exported, dict)
        assert exported["run_id"] == "run-test123"
        assert exported["message"] == "Test message"
        assert exported["metadata"] == {"key": "value"}
        assert "id" in exported
        assert "created_at" in exported

    def test_describe_returns_string(self):
        """Test describe() returns JSON string."""
        event = Event(run_id="run-test123", message="Test message")

        described = event.describe()

        assert isinstance(described, str)
        assert "run-test123" in described
        assert "Test message" in described

    def test_export_with_all_fields(self):
        """Test export with all optional fields populated."""
        event = Event(
            run_id="run-test123",
            message="Test message",
            metadata={"duration": 100},
            tags={"level": "info"},
        )

        exported = event.export()

        assert exported["run_id"] == "run-test123"
        assert exported["message"] == "Test message"
        assert exported["metadata"] == {"duration": 100}
        assert exported["tags"] == {"level": "info"}
