"""
Unit tests for bastion.domain.event.base module.
"""

from datetime import datetime

import pytest

from bastion.domain.event.base import BaseEventModel, EventKind


class TestEventKind:
    """Test EventKind enumeration."""

    def test_event_kind_values(self):
        """Test EventKind has correct base value."""
        assert EventKind.BASE == "base"

    def test_from_any_with_event_kind(self):
        """Test from_any returns same EventKind instance."""
        kind = EventKind.BASE
        result = EventKind.from_any(kind)
        assert result == kind
        assert result is kind

    def test_from_any_with_valid_string(self):
        """Test from_any converts valid string to EventKind."""
        result = EventKind.from_any("base")
        assert result == EventKind.BASE
        assert isinstance(result, EventKind)

    def test_from_any_with_invalid_string(self):
        """Test from_any raises ValueError for invalid string."""
        with pytest.raises(ValueError, match="Invalid EventKind value: invalid"):
            EventKind.from_any("invalid")


class TestBaseEventModel:
    """Test BaseEventModel class."""

    def test_create_base_event_model(self):
        """Test creating a basic event model."""
        event = BaseEventModel(
            run_id="run-12345",
            message="Test event message",
        )
        assert event.run_id == "run-12345"
        assert event.message == "Test event message"
        assert event.kind == EventKind.BASE
        assert isinstance(event.created_at, datetime)
        assert event.metadata == {}
        assert event.id != ""

    def test_create_event_with_custom_kind(self):
        """Test creating event with custom kind."""
        event = BaseEventModel(
            run_id="run-12345",
            kind=EventKind.BASE,
            message="Custom kind event",
        )
        assert event.kind == EventKind.BASE

    def test_create_event_with_metadata(self):
        """Test creating event with metadata."""
        metadata = {"key": "value", "count": 42}
        event = BaseEventModel(
            run_id="run-12345",
            message="Event with metadata",
            metadata=metadata,
        )
        assert event.metadata == metadata

    def test_export_event(self):
        """Test exporting event to dictionary."""
        event = BaseEventModel(
            run_id="run-12345",
            message="Test export",
            metadata={"test": True},
        )
        exported = event.export()

        assert isinstance(exported, dict)
        assert exported["id"] == event.id
        assert exported["run_id"] == "run-12345"
        assert exported["kind"] == "base"
        assert exported["message"] == "Test export"
        assert isinstance(exported["created_at"], str)
        assert exported["metadata"] == {"test": True}

    def test_export_created_at_is_iso_format(self):
        """Test exported created_at is in ISO format."""
        event = BaseEventModel(
            run_id="run-12345",
            message="Test ISO format",
        )
        exported = event.export()

        # Verify it's a valid ISO format string
        created_at_str = exported["created_at"]
        parsed = datetime.fromisoformat(created_at_str)
        assert isinstance(parsed, datetime)

    def test_id_generation(self):
        """Test that events have unique IDs with correct prefix."""
        event1 = BaseEventModel(run_id="run-1", message="Event 1")
        event2 = BaseEventModel(run_id="run-2", message="Event 2")

        assert event1.id != event2.id
        assert event1.id.startswith("event-")
        assert event2.id.startswith("event-")
        assert len(event1.id.split("-")[1]) == 16

    def test_default_values(self):
        """Test default field values."""
        event = BaseEventModel(
            run_id="run-12345",
            message="Test defaults",
        )
        assert event.kind == EventKind.BASE
        assert isinstance(event.created_at, datetime)
        assert event.metadata == {}
