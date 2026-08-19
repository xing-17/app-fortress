"""
Unit tests for bastion.domain.event.base module.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from bastion.domain.event import EventModel


class TestEventModel:
    """Test EventModel class."""

    def test_create_base_event_model(self):
        """Test creating a basic event model."""
        event = EventModel(
            run_id="run-123",
            message="Test event",
        )
        assert event.run_id == "run-123"
        assert event.message == "Test event"
        assert isinstance(event.created_at, datetime)
        assert event.metadata == {}
        assert event.id != ""
        assert event.id.startswith("event-")

    def test_id_generation(self):
        """Test that events have unique IDs with correct prefix."""
        event1 = EventModel(run_id="run-123")
        event2 = EventModel(run_id="run-123")

        assert event1.id != event2.id
        assert event1.id.startswith("event-")
        assert event2.id.startswith("event-")
        assert len(event1.id.split("-")[1]) == 16

    def test_missing_run_id_raises(self):
        """Test creating event without run_id raises error."""
        with pytest.raises(ValidationError):
            EventModel()

    def test_create_with_metadata(self):
        """Test creating event with metadata."""
        event = EventModel(
            run_id="run-123",
            message="EventModel with metadata",
            metadata={"key": "value", "count": 42},
        )
        assert event.metadata == {"key": "value", "count": 42}

    def test_created_at_auto_generated(self):
        """Test created_at is automatically set."""
        event = EventModel(run_id="run-123")
        assert event.created_at is not None
        assert isinstance(event.created_at, datetime)

    def test_export(self):
        """Test export method returns correct dictionary."""
        event = EventModel(
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

    def test_export_with_none_message(self):
        """Test export with None message."""
        event = EventModel(run_id="run-789")
        exported = event.export()

        assert exported["message"] is None

    def test_from_any_with_dict(self):
        """Test from_any creates model from dictionary."""
        data = {
            "id": "event-abc123def456789",
            "run_id": "run-123",
            "message": "Test event",
            "created_at": "2026-08-14T10:00:00",
            "metadata": {"key": "value"},
        }
        event = EventModel.from_any(data)
        assert event.id == "event-abc123def456789"
        assert event.run_id == "run-123"
        assert event.message == "Test event"
        assert event.created_at.year == 2026
        assert event.created_at.month == 8
        assert event.created_at.day == 14
        assert event.metadata == {"key": "value"}

    def test_from_any_with_model_instance(self):
        """Test from_any returns same instance when given model."""
        original = EventModel(run_id="run-123")
        result = EventModel.from_any(original)
        assert result is original

    def test_roundtrip_export_from_any(self):
        """Test export and from_any roundtrip conversion."""
        original = EventModel(
            run_id="run-roundtrip",
            message="Roundtrip test event",
            metadata={"priority": "high", "count": 99},
        )
        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = EventModel.from_any(exported)

        # Verify all fields match
        assert restored.id == original.id
        assert restored.run_id == original.run_id
        assert restored.message == original.message
        assert restored.created_at == original.created_at
        assert restored.metadata == original.metadata

    def test_roundtrip_with_none_message(self):
        """Test roundtrip conversion with None message."""
        original = EventModel(
            run_id="run-none-test",
            message=None,
            metadata={"status": "pending"},
        )
        exported = original.export()
        restored = EventModel.from_any(exported)

        assert restored.id == original.id
        assert restored.message is None
        assert restored.metadata == original.metadata

    def test_roundtrip_with_nested_metadata(self):
        """Test roundtrip conversion with nested metadata structures."""
        original = EventModel(
            run_id="run-nested",
            message="Complex metadata test",
            metadata={
                "level1": {
                    "level2": {
                        "level3": "deep value",
                        "numbers": [1, 2, 3],
                    },
                    "list_data": ["a", "b", "c"],
                },
                "simple": "value",
            },
        )
        exported = original.export()
        restored = EventModel.from_any(exported)

        assert restored.metadata == original.metadata
        assert restored.metadata["level1"]["level2"]["level3"] == "deep value"
        assert restored.metadata["level1"]["list_data"] == ["a", "b", "c"]

    def test_roundtrip_via_describe_json(self):
        """Test roundtrip conversion through JSON string using describe()."""
        import json

        original = EventModel(
            run_id="run-json-test",
            message="JSON roundtrip",
            metadata={"mode": "json", "version": 2},
        )
        # Serialize to JSON string
        json_str = original.describe()
        # Parse back to dict and recreate
        data = json.loads(json_str)
        restored = EventModel.from_any(data)

        assert restored.id == original.id
        assert restored.run_id == original.run_id
        assert restored.message == original.message
        assert restored.metadata == original.metadata

    def test_roundtrip_via_clone(self):
        """Test roundtrip using clone method."""
        original = EventModel(
            run_id="run-clone-test",
            message="Clone test",
            metadata={"clone": True},
        )
        # Clone without changes
        cloned = original.clone()

        # Verify deep copy behavior
        assert cloned.id == original.id
        assert cloned.run_id == original.run_id
        assert cloned.message == original.message
        assert cloned.metadata == original.metadata
        # Verify it's a different object
        assert cloned is not original
        # Verify metadata is deep copied
        cloned.metadata["new_key"] = "new_value"
        assert "new_key" not in original.metadata
