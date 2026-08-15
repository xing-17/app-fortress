from __future__ import annotations

import pytest

from bastion.metadata.event import Event


class TestEvent:
    """Test suite for Event class."""

    def test_event_initialization(self):
        """Test basic event initialization."""
        event = Event(run_id="run-123", message="Test message")
        assert event.run_id == "run-123"
        assert event.id is not None
        assert event.domain.message == "Test message"

    def test_event_with_metadata(self):
        """Test event initialization with metadata."""
        metadata = {"key": "value", "count": 42}
        event = Event(
            run_id="run-123",
            message="Test message",
            metadata=metadata,
        )
        assert event.domain.metadata == metadata

    def test_event_from_dict(self):
        """Test creating event from dictionary."""
        data = {
            "run_id": "run-123",
            "message": "Test message",
            "metadata": {"status": "ok"},
        }
        event = Event.from_any(data)
        assert event.run_id == "run-123"
        assert event.domain.message == "Test message"
        assert event.domain.metadata == {"status": "ok"}

    def test_event_from_event(self):
        """Test creating event from another event instance."""
        event1 = Event(run_id="run-123", message="Original")
        event2 = Event.from_any(event1)
        assert event1.id == event2.id
        assert event1.run_id == event2.run_id

    def test_event_export(self):
        """Test event export to dictionary."""
        event = Event(
            run_id="run-123",
            message="Test message",
            metadata={"key": "value"},
        )
        exported = event.export()
        assert exported["run_id"] == "run-123"
        assert exported["message"] == "Test message"
        assert exported["metadata"] == {"key": "value"}
        assert "id" in exported
        assert "created_at" in exported

    def test_event_sha256_key(self):
        """Test event SHA256 key generation."""
        event = Event(run_id="run-123", message="Test")
        sha_key = event._sha256_key
        assert isinstance(sha_key, str)
        assert len(sha_key) > 0

    def test_event_from_invalid_data(self):
        """Test event creation with invalid data."""
        with pytest.raises(ValueError):
            Event.from_any({"invalid": "data"})
