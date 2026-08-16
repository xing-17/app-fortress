"""
Unit tests for bastion.domain.quality.base module.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from bastion.domain.quality.base import BaseQualityModel


class TestBaseQualityModel:
    """Test BaseQualityModel class."""

    def test_create_base_quality_model(self):
        """Test creating a basic quality model."""
        quality = BaseQualityModel(
            run_id="run-123",
        )
        assert quality.run_id == "run-123"
        assert quality.kind == "base"
        assert quality.passed is None
        assert isinstance(quality.created_at, datetime)
        assert quality.metrics == {}
        assert quality.id != ""
        assert quality.id.startswith("qual-")

    def test_id_generation(self):
        """Test that quality metrics have unique IDs with correct prefix."""
        quality1 = BaseQualityModel(run_id="run-123")
        quality2 = BaseQualityModel(run_id="run-123")

        assert quality1.id != quality2.id
        assert quality1.id.startswith("qual-")
        assert quality2.id.startswith("qual-")
        assert len(quality1.id.split("-")[1]) == 20

    def test_missing_run_id_raises(self):
        """Test creating quality without run_id raises error."""
        with pytest.raises(ValidationError):
            BaseQualityModel()

    def test_create_with_kind(self):
        """Test creating quality with custom kind."""
        quality = BaseQualityModel(
            run_id="run-123",
            kind="custom",
        )
        assert quality.kind == "custom"

    def test_create_with_passed_false(self):
        """Test creating quality with passed=False."""
        quality = BaseQualityModel(
            run_id="run-123",
            passed=False,
        )
        assert quality.passed is False

    def test_create_with_metrics(self):
        """Test creating quality with metrics."""
        metrics = {
            "accuracy": 0.95,
            "precision": 0.92,
            "recall": 0.89,
        }
        quality = BaseQualityModel(
            run_id="run-123",
            metrics=metrics,
        )
        assert quality.metrics == metrics

    def test_created_at_auto_generated(self):
        """Test created_at is automatically set."""
        quality = BaseQualityModel(run_id="run-123")
        assert quality.created_at is not None
        assert isinstance(quality.created_at, datetime)

    def test_export(self):
        """Test export method returns correct dictionary."""
        quality = BaseQualityModel(
            run_id="run-456",
            kind="validation",
            passed=True,
            metrics={"score": 0.87},
        )
        exported = quality.export()

        assert exported["id"] == quality.id
        assert exported["run_id"] == "run-456"
        assert exported["kind"] == "validation"
        assert exported["passed"] is True
        assert isinstance(exported["created_at"], str)
        assert exported["metrics"] == {"score": 0.87}

        # Verify ISO format
        datetime.fromisoformat(exported["created_at"])

    def test_export_with_default_values(self):
        """Test export with default values."""
        quality = BaseQualityModel(run_id="run-789")
        exported = quality.export()

        assert exported["kind"] == "base"
        assert exported["passed"] is None
        assert isinstance(exported["created_at"], str)
        assert exported["metrics"] == {}

    def test_from_any_with_dict(self):
        """Test from_any creates model from dictionary."""
        data = {
            "id": "qual-abc123def456789012",
            "run_id": "run-123",
            "kind": "test",
            "passed": False,
            "created_at": "2026-08-14T10:00:00",
            "metrics": {"accuracy": 0.91},
        }
        quality = BaseQualityModel.from_any(data)
        assert quality.id == "qual-abc123def456789012"
        assert quality.run_id == "run-123"
        assert quality.kind == "test"
        assert quality.passed is False
        assert quality.created_at.year == 2026
        assert quality.created_at.month == 8
        assert quality.created_at.day == 14
        assert quality.metrics == {"accuracy": 0.91}

    def test_from_any_with_model_instance(self):
        """Test from_any returns same instance when given model."""
        original = BaseQualityModel(run_id="run-123")
        result = BaseQualityModel.from_any(original)
        assert result is original

    def test_roundtrip_export_from_any(self):
        """Test export and from_any roundtrip conversion."""
        original = BaseQualityModel(
            run_id="run-roundtrip",
            kind="performance",
            passed=True,
            metrics={
                "latency": 0.15,
                "throughput": 1000,
                "errors": 0,
            },
        )
        # Export to dict
        exported = original.export()
        # Recreate from dict
        restored = BaseQualityModel.from_any(exported)

        # Verify all fields match
        assert restored.id == original.id
        assert restored.run_id == original.run_id
        assert restored.kind == original.kind
        assert restored.passed == original.passed
        assert restored.created_at == original.created_at
        assert restored.metrics == original.metrics

    def test_roundtrip_with_none_values(self):
        """Test roundtrip conversion with None values."""
        original = BaseQualityModel(
            run_id="run-none-test",
            passed=None,
            description=None,
        )
        exported = original.export()
        restored = BaseQualityModel.from_any(exported)

        assert restored.id == original.id
        assert restored.passed is None
        assert restored.description is None
        assert restored.kind == "base"

    def test_roundtrip_with_passed_false(self):
        """Test roundtrip conversion with passed=False."""
        original = BaseQualityModel(
            run_id="run-failed-test",
            kind="validation",
            passed=False,
            description="Validation failed",
            metrics={"errors": 5, "warnings": 12},
        )
        exported = original.export()
        restored = BaseQualityModel.from_any(exported)

        assert restored.passed is False
        assert restored.description == "Validation failed"
        assert restored.metrics == original.metrics

    def test_roundtrip_with_nested_metrics(self):
        """Test roundtrip conversion with nested metrics structures."""
        original = BaseQualityModel(
            run_id="run-nested-metrics",
            kind="comprehensive",
            passed=True,
            metrics={
                "summary": {
                    "total": 1000,
                    "passed": 950,
                    "failed": 50,
                },
                "details": {
                    "categories": ["A", "B", "C"],
                    "scores": [0.95, 0.87, 0.92],
                },
                "timestamp": "2026-08-16T12:00:00",
            },
        )
        exported = original.export()
        restored = BaseQualityModel.from_any(exported)

        assert restored.metrics == original.metrics
        assert restored.metrics["summary"]["passed"] == 950
        assert restored.metrics["details"]["scores"] == [0.95, 0.87, 0.92]

    def test_roundtrip_via_describe_json(self):
        """Test roundtrip conversion through JSON string using describe()."""
        import json

        original = BaseQualityModel(
            run_id="run-json-test",
            kind="json-test",
            passed=True,
            description="JSON roundtrip test",
            metrics={"format": "json", "version": 1},
        )
        # Serialize to JSON string
        json_str = original.describe()
        # Parse back to dict and recreate
        data = json.loads(json_str)
        restored = BaseQualityModel.from_any(data)

        assert restored.id == original.id
        assert restored.run_id == original.run_id
        assert restored.kind == original.kind
        assert restored.passed == original.passed
        assert restored.description == original.description
        assert restored.metrics == original.metrics

    def test_roundtrip_via_clone(self):
        """Test roundtrip using clone method."""
        original = BaseQualityModel(
            run_id="run-clone-test",
            kind="clone-test",
            passed=True,
            metrics={"clone": True, "count": 42},
        )
        # Clone without changes
        cloned = original.clone()

        # Verify deep copy behavior
        assert cloned.id == original.id
        assert cloned.run_id == original.run_id
        assert cloned.kind == original.kind
        assert cloned.passed == original.passed
        assert cloned.metrics == original.metrics
        # Verify it's a different object
        assert cloned is not original
        # Verify metrics is deep copied
        cloned.metrics["new_metric"] = 99
        assert "new_metric" not in original.metrics
