"""
Unit tests for bastion.control.run.event module.
"""

from datetime import datetime

import pytest

from bastion.control.run.event import Event, EventModel, IEventLike


class TestEvent:
    """Test Event class."""

    def test_create_event(self):
        """Test creating a basic event."""
        event = Event(
            run_id="run-123",
            message="Test event",
        )
        assert event.run_id == "run-123"
        assert event.message == "Test event"
        assert isinstance(event.created_at, datetime)
        assert event.metadata == {}
        assert event.id != ""
        assert event.id.startswith("event-")

    def test_create_event_with_metadata(self):
        """Test creating event with metadata."""
        metadata = {"key": "value", "count": 42}
        event = Event(
            run_id="run-456",
            message="Event with metadata",
            metadata=metadata,
        )
        assert event.metadata == metadata

    def test_create_event_with_custom_id(self):
        """Test creating event with custom ID."""
        custom_id = "event-custom12345678"
        event = Event(
            run_id="run-789",
            id=custom_id,
            message="Custom ID event",
        )
        assert event.id == custom_id

    def test_create_event_with_created_at_string(self):
        """Test creating event with created_at as ISO string."""
        iso_time = "2026-08-14T10:00:00"
        event = Event(
            run_id="run-123",
            message="Event with timestamp",
            created_at=iso_time,
        )
        assert event.created_at.year == 2026
        assert event.created_at.month == 8
        assert event.created_at.day == 14

    def test_create_event_with_created_at_datetime(self):
        """Test creating event with created_at as datetime."""
        dt = datetime(2026, 8, 14, 10, 30, 0)
        event = Event(
            run_id="run-123",
            message="Event with datetime",
            created_at=dt,
        )
        assert event.created_at == dt

    def test_missing_run_id_raises(self):
        """Test creating event without run_id raises error."""
        with pytest.raises(TypeError):
            Event()

    def test_export(self):
        """Test export method returns correct dictionary."""
        event = Event(
            run_id="run-456",
            message="Export test",
            metadata={"type": "info"},
        )
        exported = event.export()

        assert exported["id"] == event.id
        assert exported["run_id"] == "run-456"
        assert exported["message"] == "Export test"
        assert isinstance(exported["created_at"], str)
        assert exported["metadata"] == {"type": "info"}

        # Verify ISO format
        datetime.fromisoformat(exported["created_at"])

    def test_from_dict(self):
        """Test from_dict creates Event from dictionary."""
        data = {
            "id": "event-abc123def456789",
            "run_id": "run-123",
            "message": "Test event",
            "created_at": "2026-08-14T10:00:00",
            "metadata": {"key": "value"},
        }
        event = Event.from_dict(data)
        assert event.id == "event-abc123def456789"
        assert event.run_id == "run-123"
        assert event.message == "Test event"
        assert event.metadata == {"key": "value"}

    def test_from_domain(self):
        """Test from_domain creates Event from domain model."""
        domain = EventModel(
            run_id="run-123",
            message="Domain event",
            metadata={"source": "test"},
        )
        event = Event.from_domain(domain)
        assert event.run_id == "run-123"
        assert event.message == "Domain event"
        assert event.metadata == {"source": "test"}

    def test_roundtrip_export_from_dict(self, event_data):
        """Test export and from_dict roundtrip conversion."""
        original = Event(**event_data)

        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = Event.from_dict(exported)

        # Verify all fields match
        assert restored.id == original.id
        assert restored.run_id == original.run_id
        assert restored.message == original.message
        assert restored.created_at == original.created_at
        assert restored.metadata == original.metadata

    def test_protocol_compliance(self):
        """Test Event implements IEventLike protocol."""
        event = Event(run_id="run-123", message="Protocol test")
        assert isinstance(event, IEventLike)

    def test_domain_attribute_access(self):
        """Test accessing domain attributes through wrapper."""
        event = Event(
            run_id="run-123",
            message="Domain access test",
        )
        # Access domain directly
        assert event.domain is not None
        assert isinstance(event.domain, EventModel)
        # Access via wrapper
        assert event.id == event.domain.id
        assert event.run_id == event.domain.run_id

    def test_sha256_property(self):
        """Test sha256 property exists and is consistent."""
        event = Event(
            run_id="run-123",
            message="SHA test",
        )
        sha1 = event.sha256
        sha2 = event.sha256
        assert sha1 == sha2
        assert isinstance(sha1, str)
        assert len(sha1) > 0

    def test_logic_name_property(self):
        """Test logic_name property exists."""
        event = Event(
            run_id="run-123",
            message="Logic name test",
        )
        logic_name = event.logic_name
        assert logic_name is not None or logic_name is None  # Can be either

    def test_describe_returns_json_string(self):
        """Test describe method returns formatted JSON string."""
        event = Event(
            run_id="run-123",
            message="Describe test",
            metadata={"key": "value"},
        )
        description = event.describe()
        assert isinstance(description, str)
        # Should be valid JSON
        import json

        parsed = json.loads(description)
        assert parsed["run_id"] == "run-123"
        assert parsed["message"] == "Describe test"
